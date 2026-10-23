package com.chiranjit.authService.security;

import com.nimbusds.jose.JOSEException;
import com.nimbusds.jose.jwk.JWKSet;
import com.nimbusds.jose.jwk.KeyUse;
import com.nimbusds.jose.jwk.RSAKey;
import com.nimbusds.jose.jwk.gen.RSAKeyGenerator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.text.ParseException;
import java.util.Map;

/**
 * The RSA key pair this service signs with.
 *
 * RSA rather than a shared secret, because the whole point of a separate auth
 * service is that nothing else can mint tokens. With HS256 every verifier holds
 * the signing key and could issue itself an administrator token; with RS256 the
 * private half never leaves this process and verifiers get only the public half
 * from {@code /.well-known/jwks.json}.
 */
@Component
public class SigningKeys {

	private static final Logger log = LoggerFactory.getLogger(SigningKeys.class);

	private static final int KEY_SIZE = 2048;

	private final RSAKey key;

	public SigningKeys(@Value("${app.jwt.key-file:keys/auth-signing-key.jwk}") Path keyFile)
			throws JOSEException, IOException {

		this.key = load(keyFile).orElseGet(() -> generate(keyFile));
		log.info("Signing tokens with RS256, key id {}", this.key.getKeyID());
	}

	private static java.util.Optional<RSAKey> load(Path keyFile) {
		if (keyFile == null || !Files.isRegularFile(keyFile)) {
			return java.util.Optional.empty();
		}
		try {
			RSAKey loaded = RSAKey.parse(Files.readString(keyFile, StandardCharsets.UTF_8));
			if (loaded.toPrivateKey() == null) {
				throw new IllegalStateException(keyFile + " holds a public key; it must hold the private one.");
			}
			return java.util.Optional.of(loaded);
		}
		catch (ParseException | IOException | JOSEException ex) {
			// Refusing is the safe answer. Quietly generating a new key instead
			// would invalidate every token in circulation and look like a bug
			// somewhere else entirely.
			throw new IllegalStateException("Could not read the signing key at " + keyFile
					+ ". Fix it or delete it to have a new one generated.", ex);
		}
	}

	/**
	 * Generates a key pair and writes it beside the service.
	 *
	 * Persisted rather than held in memory so a restart does not invalidate
	 * every token that is still in its hour of validity. The file is a private
	 * key: it is gitignored, and a real deployment should mount it as a secret
	 * rather than let it be generated.
	 */
	private static RSAKey generate(Path keyFile) {
		try {
			RSAKey generated = new RSAKeyGenerator(KEY_SIZE)
					.keyUse(KeyUse.SIGNATURE)
					// A key id, so a verifier can pick the right key out of the
					// set and so the pair can be rotated without a flag day.
					.keyIDFromThumbprint(true)
					.generate();

			if (keyFile != null) {
				if (keyFile.getParent() != null) {
					Files.createDirectories(keyFile.getParent());
				}
				Files.writeString(keyFile, generated.toJSONString(), StandardCharsets.UTF_8,
						StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
				log.warn("No signing key existed, so one was generated and written to {}. "
						+ "It is a private key: keep it out of version control, and mount it as a "
						+ "secret in anything but local development.", keyFile.toAbsolutePath());
			}
			return generated;
		}
		catch (JOSEException | IOException ex) {
			throw new IllegalStateException("Could not generate a signing key", ex);
		}
	}

	/** The private key, for signing. Never leaves this service. */
	public RSAKey signingKey() {
		return this.key;
	}

	/**
	 * The public half, in the shape a verifier expects.
	 *
	 * {@code toPublicJWK()} is what keeps the private exponent out of the
	 * response — serialising the key itself would publish the ability to forge
	 * every token this service has ever issued.
	 */
	public Map<String, Object> publicJwks() {
		return new JWKSet(this.key.toPublicJWK()).toJSONObject();
	}

	/** The public set, for verifying this service's own tokens in-process. */
	public JWKSet publicJwkSet() {
		return new JWKSet(this.key.toPublicJWK());
	}

}
