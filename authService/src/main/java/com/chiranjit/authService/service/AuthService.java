package com.chiranjit.authService.service;

import com.chiranjit.authService.dto.LoginRequest;
import com.chiranjit.authService.dto.LoginResponse;
import com.chiranjit.authService.dto.RegisterRequest;
import com.chiranjit.authService.dto.UserResponse;
import com.chiranjit.authService.entity.AppUser;
import com.chiranjit.authService.entity.Role;
import com.chiranjit.authService.repository.AppUserRepository;
import com.chiranjit.authService.security.JwtIssuer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.List;
import java.util.Locale;
import java.util.Optional;

@Service
public class AuthService {

	private static final Logger log = LoggerFactory.getLogger(AuthService.class);

	/**
	 * One message for every failure. Saying "no such user" would turn this
	 * endpoint into a way to enumerate who has an account.
	 */
	private static final String REJECTED = "Invalid username or password.";

	private final AppUserRepository appUserRepository;

	private final PasswordEncoder passwordEncoder;

	private final JwtIssuer jwtIssuer;

	/**
	 * A hash of a value nothing will ever submit, so an unknown username costs
	 * the same time to reject as a known one.
	 *
	 * Built with the injected encoder rather than a fresh one: a dummy hashed at
	 * a different work factor would take a different amount of time to check,
	 * which is exactly the signal this is here to remove.
	 */
	private final String dummyHash;

	public AuthService(AppUserRepository appUserRepository, PasswordEncoder passwordEncoder,
			JwtIssuer jwtIssuer) {

		this.appUserRepository = appUserRepository;
		this.passwordEncoder = passwordEncoder;
		this.jwtIssuer = jwtIssuer;
		this.dummyHash = passwordEncoder.encode("no account matches this value");
	}

	public LoginResponse login(LoginRequest request) {
		String username = normalise(request.username());
		Optional<AppUser> found = this.appUserRepository.findByUsername(username);

		// The password is verified even when no account was found. Returning
		// early on an unknown username makes that case measurably faster to
		// answer, and the difference is enough to enumerate accounts with a
		// stopwatch.
		String hash = found.map(AppUser::getPasswordHash).orElse(this.dummyHash);
		boolean matches = this.passwordEncoder.matches(request.password(), hash);

		if (found.isEmpty() || !matches) {
			log.info("Failed login for '{}'", username);
			throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, REJECTED);
		}

		AppUser user = found.get();
		if (!user.isEnabled()) {
			// Deliberately the same message: whether an account exists but is
			// switched off is not something an unauthenticated caller should
			// learn.
			log.info("Login refused for disabled account '{}'", username);
			throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, REJECTED);
		}

		log.info("Issued a token to '{}' ({})", username, user.getRole());
		return new LoginResponse(this.jwtIssuer.issue(user), "Bearer", this.jwtIssuer.expirySeconds(),
				user.getUsername(), user.getRole().name());
	}

	public UserResponse register(RegisterRequest request) {
		String username = normalise(request.username());
		if (this.appUserRepository.existsByUsername(username)) {
			throw new ResponseStatusException(HttpStatus.CONFLICT, "That username is taken.");
		}
		return toResponse(create(username, request.password(), request.role()));
	}

	/** Shared by registration and the first-run bootstrap. */
	public AppUser create(String username, String rawPassword, Role role) {
		AppUser user = new AppUser();
		user.setUsername(normalise(username));
		user.setPasswordHash(this.passwordEncoder.encode(rawPassword));
		user.setRole(role);
		user.setEnabled(true);
		user.setCreatedAt(Instant.now());
		return this.appUserRepository.save(user);
	}

	/** Every account, newest last. Never includes password material. */
	public List<UserResponse> listUsers() {
		return this.appUserRepository.findAll()
				.stream()
				.sorted(java.util.Comparator.comparing(AppUser::getCreatedAt,
						java.util.Comparator.nullsFirst(java.util.Comparator.naturalOrder())))
				.map(AuthService::toResponse)
				.toList();
	}

	public UserResponse describe(String username) {
		return this.appUserRepository.findByUsername(normalise(username))
				.map(AuthService::toResponse)
				.orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "No such account."));
	}

	/**
	 * Lowercased and trimmed, so an account cannot be shadowed by one differing
	 * only in case or surrounding space.
	 */
	private static String normalise(String username) {
		return username == null ? "" : username.trim().toLowerCase(Locale.ROOT);
	}

	private static UserResponse toResponse(AppUser user) {
		return new UserResponse(user.getId(), user.getUsername(), user.getRole(), user.isEnabled(),
				user.getCreatedAt());
	}

}
