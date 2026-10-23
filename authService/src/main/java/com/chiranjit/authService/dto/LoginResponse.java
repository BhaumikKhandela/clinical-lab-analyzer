package com.chiranjit.authService.dto;

/** A freshly issued token and what the caller needs to use it. */
public record LoginResponse(

		String token,

		String tokenType,

		long expiresIn,

		String username,

		String role) {

}
