package com.chiranjit.authService.security;

import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.proc.JWSVerificationKeySelector;
import com.nimbusds.jose.proc.SecurityContext;
import com.nimbusds.jose.jwk.source.ImmutableJWKSet;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.proc.DefaultJWTClaimsVerifier;
import com.nimbusds.jwt.proc.DefaultJWTProcessor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.Set;
import java.util.UUID;

/**
 * Verifies tokens this service issued, for its own protected endpoints.
 *
 * It verifies with the *public* key through the same JWKS machinery a resource
 * server uses, rather than reaching for the private key it happens to have in
 * memory. That keeps one code path for verification and means this service is
 * not a special case that could drift from how everything else behaves.
 */
@Component
public class TokenVerifier {

	private final DefaultJWTProcessor<SecurityContext> processor;

	public TokenVerifier(SigningKeys keys, @Value("${app.jwt.issuer:lab-analyzer-auth}") String issuer) {
		this.processor = new DefaultJWTProcessor<>();

		// Pinned to RS256. Without this the processor would accept whatever the
		// token's own header asks for, which is how algorithm-confusion works.
		this.processor.setJWSKeySelector(new JWSVerificationKeySelector<>(
				JWSAlgorithm.RS256, new ImmutableJWKSet<>(keys.publicJwkSet())));

		// Issuer must match and expiry must be present: a token with no `exp`
		// would otherwise be valid forever.
		this.processor.setJWTClaimsSetVerifier(new DefaultJWTClaimsVerifier<>(
				new JWTClaimsSet.Builder().issuer(issuer).build(),
				Set.of("sub", "exp", "uid", "role")));
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
			// issuer, missing claim — ends as the same 401. The reason is kept
			// for the log, not widened into something a caller can probe with.
			return new Verification(false, ex.getMessage(), null, null, null);
		}
	}

	public record Verification(boolean valid, String reason, String username, String role, UUID userId) {

	}

}
