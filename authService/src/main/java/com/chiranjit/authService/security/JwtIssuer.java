package com.chiranjit.authService.security;

import com.chiranjit.authService.entity.AppUser;
import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.JWSHeader;
import com.nimbusds.jose.crypto.RSASSASigner;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.SignedJWT;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;
import java.util.Date;

/**
 * Signs the tokens every other service trusts.
 *
 * The only place in the system that can do this: the private key lives here and
 * is published nowhere.
 */
@Component
public class JwtIssuer {

	private final SigningKeys keys;

	private final String issuer;

	private final Duration expiry;

	private final RSASSASigner signer;

	public JwtIssuer(SigningKeys keys, @Value("${app.jwt.issuer:lab-analyzer-auth}") String issuer,
			@Value("${app.jwt.expiry-seconds:3600}") long expirySeconds) throws JOSEException {

		this.keys = keys;
		this.issuer = issuer;
		this.expiry = Duration.ofSeconds(expirySeconds);
		this.signer = new RSASSASigner(keys.signingKey());
	}

	public String issue(AppUser user) {
		Instant now = Instant.now();
		try {
			JWTClaimsSet claims = new JWTClaimsSet.Builder()
					.subject(user.getUsername())
					.issuer(this.issuer)
					.issueTime(Date.from(now))
					.expirationTime(Date.from(now.plus(this.expiry)))
					// Carried so a resource server can attribute a request
					// without calling back here on every call.
					.claim("uid", user.getId().toString())
					.claim("role", user.getRole().name())
					.build();

			// The key id goes in the header so a verifier can pick the right key
			// out of the JWKS — which is what makes rotation possible without
			// invalidating tokens signed by the outgoing key.
			JWSHeader header = new JWSHeader.Builder(JWSAlgorithm.RS256)
					.keyID(this.keys.signingKey().getKeyID())
					.build();

			SignedJWT jwt = new SignedJWT(header, claims);
			jwt.sign(this.signer);
			return jwt.serialize();
		}
		catch (JOSEException ex) {
			throw new IllegalStateException("Could not sign a token", ex);
		}
	}

	public long expirySeconds() {
		return this.expiry.toSeconds();
	}

}
