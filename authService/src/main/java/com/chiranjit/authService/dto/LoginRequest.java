package com.chiranjit.authService.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record LoginRequest(

		@NotBlank @Size(max = 64) String username,

		// Bounded so an enormous string cannot be fed to BCrypt as a cheap way
		// to tie up a thread.
		@NotBlank @Size(max = 200) String password) {

}
