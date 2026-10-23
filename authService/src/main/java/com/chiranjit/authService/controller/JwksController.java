package com.chiranjit.authService.controller;

import com.chiranjit.authService.security.SigningKeys;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * Publishes the public half of the signing key.
 *
 * Deliberately unauthenticated: a public key is public, and every service that
 * verifies a token needs it before it can authenticate anything. Serving it at
 * the standard path means a resource server can be pointed at this service
 * without being told where to look.
 */
@RestController
public class JwksController {

	private final SigningKeys keys;

	public JwksController(SigningKeys keys) {
		this.keys = keys;
	}

	@GetMapping("/.well-known/jwks.json")
	public Map<String, Object> jwks() {
		return this.keys.publicJwks();
	}

}
