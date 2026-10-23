package com.chiranjit.authService.dto;

import com.chiranjit.authService.entity.Role;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record RegisterRequest(

		// Letters, digits, dot, dash and underscore: enough for real usernames,
		// narrow enough that nothing here needs escaping downstream.
		@NotBlank @Size(min = 3, max = 64) @Pattern(regexp = "[A-Za-z0-9._-]+") String username,

		// A length floor and nothing else. Composition rules push people toward
		// predictable substitutions; length is what actually costs an attacker.
		@NotBlank @Size(min = 12, max = 200) String password,

		@NotNull Role role) {

}
