package com.chiranjit.authService.dto;

import com.chiranjit.authService.entity.Role;

import java.time.Instant;
import java.util.UUID;

/** An account, without anything that could help impersonate it. */
public record UserResponse(

		UUID id,

		String username,

		Role role,

		boolean enabled,

		Instant createdAt) {

}
