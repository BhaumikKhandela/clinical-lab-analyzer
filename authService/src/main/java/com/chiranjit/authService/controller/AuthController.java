package com.chiranjit.authService.controller;

import com.chiranjit.authService.dto.LoginRequest;
import com.chiranjit.authService.dto.LoginResponse;
import com.chiranjit.authService.dto.RegisterRequest;
import com.chiranjit.authService.dto.UserResponse;
import com.chiranjit.authService.security.AdminPassphrase;
import com.chiranjit.authService.security.JwtAuthenticationFilter.AuthenticatedUser;
import com.chiranjit.authService.service.AuthService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

	/** The header the admin page sends its passphrase in. */
	private static final String PASSPHRASE_HEADER = "X-Admin-Passphrase";

	private final AuthService authService;

	private final AdminPassphrase adminPassphrase;

	/**
	 * Exchanges a username and password for a token.
	 *
	 * The only endpoint on this service reachable without one, which is why
	 * SecurityConfig names it explicitly rather than opening a path prefix.
	 */
	@PostMapping("/login")
	public LoginResponse login(@Valid @RequestBody LoginRequest request) {
		return this.authService.login(request);
	}

	/**
	 * Unlocks the admin page.
	 *
	 * Exists so the page can check the passphrase before showing a form, rather
	 * than letting someone fill one in and discover at the end that they cannot
	 * submit it. It grants nothing on its own — every create is checked again.
	 */
	@PostMapping("/admin/unlock")
	@ResponseStatus(HttpStatus.NO_CONTENT)
	public void unlock(@RequestHeader(PASSPHRASE_HEADER) String passphrase) {
		this.adminPassphrase.require(passphrase);
	}

	/**
	 * Creates an account.
	 *
	 * Two gates, not one: an ADMIN token to reach the endpoint at all (pinned in
	 * SecurityConfig), and the passphrase on every call. The passphrase is
	 * re-checked here rather than trusted from the earlier unlock, because
	 * nothing on the client is in a position to vouch for it.
	 */
	@PostMapping("/register")
	@ResponseStatus(HttpStatus.CREATED)
	public UserResponse register(@RequestHeader(PASSPHRASE_HEADER) String passphrase,
			@Valid @RequestBody RegisterRequest request) {

		this.adminPassphrase.require(passphrase);
		return this.authService.register(request);
	}

	/** Every account, so the admin page can show what already exists. */
	@GetMapping("/users")
	public List<UserResponse> users(@RequestHeader(PASSPHRASE_HEADER) String passphrase) {
		this.adminPassphrase.require(passphrase);
		return this.authService.listUsers();
	}

	/** Who the current token says you are. Useful for a client checking validity. */
	@GetMapping("/me")
	public UserResponse me(@AuthenticationPrincipal AuthenticatedUser caller) {
		return this.authService.describe(caller.username());
	}

}
