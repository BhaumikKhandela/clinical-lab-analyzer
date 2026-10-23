package com.chiranjit.patientService.security;

import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.jwk.source.JWKSource;
import com.nimbusds.jose.jwk.source.JWKSourceBuilder;
import com.nimbusds.jose.proc.JWSVerificationKeySelector;
import com.nimbusds.jose.proc.SecurityContext;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.proc.DefaultJWTClaimsVerifier;
import com.nimbusds.jwt.proc.DefaultJWTProcessor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.net.MalformedURLException;
import java.net.URI;
import java.net.URL;
import java.util.Set;
import java.util.UUID;

/**
 * Verifies tokens the auth service issued.
 *
 * This service holds no signing key and cannot mint a token — that is the whole
 * reason authentication was split out. It fetches the public half from the auth
 * service's JWKS endpoint and checks signatures with it.
 *
 * The key set is fetched lazily on the first token, then cached and refreshed
 * by the JWK source. That means a restart of the auth service, or a key
 * rotation, is picked up without restarting this one — and that this service
 * starts fine when the auth service is not up yet.
 */
@Component
public class TokenVerifier {

	private static final Logger log = LoggerFactory.getLogger(TokenVerifier.class);

	private final DefaultJWTProcessor<SecurityContext> processor;

	public TokenVerifier(
			@Value("${app.auth.jwks-uri:http://127.0.0.1:8085/.well-known/jwks.json}") String jwksUri,
			@Value("${app.auth.issuer:lab-analyzer-auth}") String issuer) throws MalformedURLException {

		URL url = URI.create(jwksUri).toURL();

		// Caches the key set, refreshes it when an unknown key id appears, and
		// rate-limits that refresh so a flood of bad tokens cannot be turned
		// into a flood of requests at the auth service.
		JWKSource<SecurityContext> keys = JWKSourceBuilder.create(url)
				.retrying(true)
				.build();

		this.processor = new DefaultJWTProcessor<>();

		// Pinned to RS256. Without this the processor would accept whatever the
		// token's own header asks for, which is how algorithm confusion works —
		// and this service holds no symmetric key for anything to confuse it
		// with, which is itself a reason the split is worth having.
		this.processor.setJWSKeySelector(new JWSVerificationKeySelector<>(JWSAlgorithm.RS256, keys));

		// Issuer must match, and these claims must be present: a token with no
		// `exp` would otherwise be valid forever.
		this.processor.setJWTClaimsSetVerifier(new DefaultJWTClaimsVerifier<>(
				new JWTClaimsSet.Builder().issuer(issuer).build(),
				Set.of("sub", "exp", "uid", "role")));

		log.info("Verifying tokens from {} against {}", issuer, jwksUri);
	}

	/** Who the token says this is, or why it was refused. */
	public Verification verify(String token) {
		try {
			JWTClaimsSet claims = this.processor.process(token, null);
			return new Verification(true, null, claims.getSubject(),
					claims.getStringClaim("role"), UUID.fromString(claims.getStringClaim("uid")));
		}
		catch (Exception ex) {
			// Every failure mode — malformed, bad signature, expired, wrong
			// issuer, missing claim, auth service unreachable — ends as the same
			// 401. The reason is kept for the log rather than widened into
			// something a caller can probe with.
			return new Verification(false, ex.getMessage(), null, null, null);
		}
	}

	public record Verification(boolean valid, String reason, String username, String role, UUID userId) {

	}

}
