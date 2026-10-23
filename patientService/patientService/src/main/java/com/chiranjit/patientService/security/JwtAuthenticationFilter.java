package com.chiranjit.patientService.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.jspecify.annotations.NonNull;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

/**
 * Turns a bearer token into an authenticated request, or into a 401.
 *
 * {@link OncePerRequestFilter} rather than a bare servlet filter: Spring's
 * dispatcher can run a request through the chain more than once (a forward to
 * an error page, for instance), and authenticating twice is at best wasted work
 * and at worst a second chance for a malformed header to be interpreted
 * differently.
 *
 * The tokens come from the auth service; this service only verifies them and
 * cannot issue one.
 *
 * The filter does not decide *what* is public — {@link SecurityConfig} does.
 * Here, a request with no token simply passes through unauthenticated, and the
 * authorization rules reject it later if it needed to be authenticated. That
 * split is what lets the login endpoint work without a special case here.
 */
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

	private static final Logger log = LoggerFactory.getLogger(JwtAuthenticationFilter.class);

	private static final String PREFIX = "Bearer ";

	/** Spring Security expects authorities to be role names with this prefix. */
	private static final String ROLE_PREFIX = "ROLE_";

	private final TokenVerifier tokenVerifier;

	public JwtAuthenticationFilter(TokenVerifier tokenVerifier) {
		this.tokenVerifier = tokenVerifier;
	}

	/**
	 * CORS preflight carries no credentials by definition, so authenticating it
	 * would reject every cross-origin request before the real one was ever sent.
	 */
	@Override
	protected boolean shouldNotFilter(@NonNull HttpServletRequest request) {
		return "OPTIONS".equalsIgnoreCase(request.getMethod());
	}

	@Override
	protected void doFilterInternal(@NonNull HttpServletRequest request, @NonNull HttpServletResponse response,
			@NonNull FilterChain chain) throws ServletException, IOException {

		String header = request.getHeader(HttpHeaders.AUTHORIZATION);

		// No token at all is not an error here. Public endpoints need to work,
		// and anything else is refused by the authorization rules downstream
		// with a 401 from the entry point.
		if (header == null || !header.startsWith(PREFIX)) {
			chain.doFilter(request, response);
			return;
		}

		String token = header.substring(PREFIX.length()).trim();
		TokenVerifier.Verification result = this.tokenVerifier.verify(token);

		if (!result.valid()) {
			// A token that was *offered* and is bad is a different case: letting
			// it through unauthenticated would surface as a confusing 401 from
			// somewhere else, with no indication that the token was the problem.
			log.debug("Rejected a token on {} {}: {}", request.getMethod(), request.getRequestURI(),
					result.reason());
			// Nothing a rejected caller sends can be trusted, so the context is
			// cleared before responding rather than assumed to be empty.
			SecurityContextHolder.clearContext();
			unauthorized(response);
			return;
		}

		UsernamePasswordAuthenticationToken authentication = new UsernamePasswordAuthenticationToken(
				new AuthenticatedUser(result.userId(), result.username(), result.role()),
				// No credentials are retained: the token has already been
				// verified and keeping it on the context only widens what a log
				// or a heap dump could leak.
				null,
				List.of(new SimpleGrantedAuthority(ROLE_PREFIX + result.role())));

		authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
		SecurityContextHolder.getContext().setAuthentication(authentication);

		try {
			chain.doFilter(request, response);
		}
		finally {
			// Threads are pooled and reused. Leaving an authentication behind
			// would hand the next request on this thread someone else's identity.
			SecurityContextHolder.clearContext();
		}
	}

	private static void unauthorized(HttpServletResponse response) throws IOException {
		response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
		response.setContentType(MediaType.APPLICATION_JSON_VALUE);
		// One message for every rejection. The specific reason is in the log,
		// where it helps an operator, rather than in the response, where it only
		// helps someone probing the token format.
		response.getWriter().write("{\"error\":\"unauthorized\",\"message\":\"That token was rejected.\"}");
	}

	/** Who the current request is, as put on the security context. */
	public record AuthenticatedUser(java.util.UUID id, String username, String role) {

		@Override
		public String toString() {
			return this.username;
		}

	}

}
