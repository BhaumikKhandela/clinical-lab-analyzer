package com.chiranjit.authService.security;

import com.chiranjit.authService.entity.AppUser;
import com.chiranjit.authService.entity.Role;
import com.chiranjit.authService.repository.AppUserRepository;
import com.chiranjit.authService.service.AuthService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

import java.security.SecureRandom;
import java.util.Base64;

/**
 * Creates the first administrator, once, on an empty user table.
 *
 * Without this a secured service has no way in: every endpoint needs a token,
 * tokens come from logging in, and logging in needs an account that only an
 * administrator can create. Something has to break that circle, and a
 * first-run account is the narrowest thing that does — it stops applying the
 * moment one account exists.
 */
@Component
public class AuthBootstrap implements ApplicationRunner {

	private static final Logger log = LoggerFactory.getLogger(AuthBootstrap.class);

	private final AppUserRepository appUserRepository;

	private final AuthService authService;

	@Value("${app.auth.bootstrap-username:admin}")
	private String username;

	@Value("${app.auth.bootstrap-password:}")
	private String password;

	public AuthBootstrap(AppUserRepository appUserRepository, AuthService authService) {
		this.appUserRepository = appUserRepository;
		this.authService = authService;
	}

	@Override
	public void run(ApplicationArguments args) {
		// Keyed on the table being empty, not on the username being free: once
		// anybody has an account, this service is no longer in its first run and
		// account creation belongs to an administrator.
		if (this.appUserRepository.count() > 0) {
			return;
		}

		boolean generated = this.password == null || this.password.isBlank();
		String raw = generated ? randomPassword() : this.password;

		AppUser created = this.authService.create(this.username, raw, Role.ADMIN);

		if (generated) {
			// Printed once and never stored in readable form. A fixed default
			// would be the same on every deployment of this project, which is
			// the kind of credential that ends up in a scanner's wordlist.
			log.warn("""

					  No administrator existed, so one was created.

					    username: {}
					    password: {}

					  This password is shown once and is not recoverable — it is stored
					  only as a hash. Set app.auth.bootstrap-password (or APP_AUTH_BOOTSTRAP_PASSWORD)
					  to choose it yourself.
					""", created.getUsername(), raw);
		}
		else {
			log.info("No administrator existed, so '{}' was created from configuration.",
					created.getUsername());
		}
	}

	/** 24 random bytes, URL-safe: long enough that guessing is not the weak point. */
	private static String randomPassword() {
		byte[] bytes = new byte[24];
		new SecureRandom().nextBytes(bytes);
		return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
	}

}
