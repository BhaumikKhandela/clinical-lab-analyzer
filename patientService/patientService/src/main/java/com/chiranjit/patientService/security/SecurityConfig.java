package com.chiranjit.patientService.security;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.Arrays;
import java.util.List;

/**
 * What is public, what needs a token, and where the filter sits.
 *
 * Tokens are issued by the auth service and merely verified here, so this
 * service has no login endpoint and nothing public under /api.
 *
 * Everything under /api is closed by default and opened one path at a time.
 * Written that way round on purpose: a new endpoint added later is protected
 * because nobody remembered to protect it, rather than exposed because nobody
 * remembered to list it.
 */
@Configuration
@EnableMethodSecurity
public class SecurityConfig {

	private final JwtAuthenticationFilter jwtAuthenticationFilter;

	@Value("${app.cors-origins:http://localhost:5173,http://127.0.0.1:5173}")
	private String[] corsOrigins;

	public SecurityConfig(JwtAuthenticationFilter jwtAuthenticationFilter) {
		this.jwtAuthenticationFilter = jwtAuthenticationFilter;
	}

	@Bean
	SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
		http
				// Disabled because there is no session and no cookie to forge a
				// request against: the credential is a header the browser will
				// not attach on its own. With cookie auth this would have to
				// come back.
				.csrf(csrf -> csrf.disable())
				.cors(cors -> cors.configurationSource(corsConfigurationSource()))
				.sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
				.authorizeHttpRequests(auth -> auth
						// Preflight carries no credentials; rejecting it breaks
						// every cross-origin call before it is made.
						.requestMatchers(HttpMethod.OPTIONS, "/**").permitAll()
						// Signing in happens at the auth service. There is no
						// public endpoint on this one at all.
						.requestMatchers("/actuator/health", "/error").permitAll()
						.anyRequest().authenticated())
				.exceptionHandling(ex -> ex
						.authenticationEntryPoint((request, response, failure) -> {
							// The default entry point answers with a redirect or
							// a WWW-Authenticate challenge, either of which makes
							// a browser pop a basic-auth dialog at an API caller.
							response.setStatus(401);
							response.setContentType(MediaType.APPLICATION_JSON_VALUE);
							response.getWriter().write(
									"{\"error\":\"unauthorized\",\"message\":\"Authentication is required.\"}");
						})
						.accessDeniedHandler((request, response, failure) -> {
							response.setStatus(403);
							response.setContentType(MediaType.APPLICATION_JSON_VALUE);
							response.getWriter().write(
									"{\"error\":\"forbidden\",\"message\":\"Your account may not do that.\"}");
						}))
				// Before the username/password filter, which is where the chain
				// would otherwise start looking for a form login this service
				// does not have.
				.addFilterBefore(this.jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);

		return http.build();
	}

	/**
	 * CORS for the security chain.
	 *
	 * WebConfig's addCorsMappings configures Spring MVC, and the security filter
	 * chain runs before MVC is reached — so without a source here, preflight is
	 * rejected at the filter and the browser reports an opaque CORS failure with
	 * no hint that authentication was involved.
	 */
	@Bean
	CorsConfigurationSource corsConfigurationSource() {
		CorsConfiguration configuration = new CorsConfiguration();
		configuration.setAllowedOrigins(Arrays.asList(this.corsOrigins));
		configuration.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE", "OPTIONS"));
		configuration.setAllowedHeaders(List.of("*"));
		// So a browser client can read it back off a login response if it ever
		// needs to; the token itself travels in the body.
		configuration.setExposedHeaders(List.of("Authorization"));

		UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
		source.registerCorsConfiguration("/api/**", configuration);
		return source;
	}

}
