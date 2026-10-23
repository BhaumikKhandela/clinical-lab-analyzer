package com.chiranjit.authService.security;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/**
 * A fixed passphrase guarding account creation, on top of the ADMIN role.
 *
 * Deliberately checked here and not in the browser. A value compiled into the
 * frontend bundle is readable by anyone who opens developer tools, so a page
 * that only asks the browser to compare it is a locked door with the key taped
 * to it. The page still prompts — but what makes the prompt mean anything is
 * that the answer is verified on this side.
 *
 * It is a second factor, not the only one: a caller still needs an ADMIN token
 * to reach these endpoints at all.
 */
@Component
public class AdminPassphrase {

	/**
	 * The hardcoded default. Fine for a project that runs on one machine;
	 * override it with APP_AUTH_ADMIN_PASSPHRASE anywhere real, since this value
	 * is in the repository and therefore public.
	 */
	private final String expected;

	public AdminPassphrase(
			@Value("${app.auth.admin-passphrase:let-me-in-and-make-accounts}") String expected) {
		this.expected = expected;
	}

	/** Throws 403 unless the supplied passphrase matches. */
	public void require(String supplied) {
		if (!matches(supplied)) {
			throw new ResponseStatusException(HttpStatus.FORBIDDEN, "That admin passphrase is wrong.");
		}
	}

	public boolean matches(String supplied) {
		if (supplied == null) {
			return false;
		}
		// Constant-time: a plain equals() returns as soon as two characters
		// differ, and that timing difference is enough to recover the value one
		// character at a time.
		return MessageDigest.isEqual(
				supplied.getBytes(StandardCharsets.UTF_8),
				this.expected.getBytes(StandardCharsets.UTF_8));
	}

}
