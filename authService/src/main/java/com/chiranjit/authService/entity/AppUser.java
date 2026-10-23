package com.chiranjit.authService.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.Setter;

import java.time.Instant;
import java.util.UUID;

/** An account that may call this service. */
@Entity
@Table(name = "app_user")
@Getter
@Setter
public class AppUser {

	@Id
	@GeneratedValue(strategy = GenerationType.UUID)
	private UUID id;

	/** Stored lowercase, so usernames cannot collide only by case. */
	@Column(unique = true)
	private String username;

	/**
	 * A BCrypt hash. Named for what it holds so that nothing in this codebase
	 * reads as though it has a password to hand.
	 */
	private String passwordHash;

	@Enumerated(EnumType.STRING)
	private Role role;

	private boolean enabled;

	private Instant createdAt;

}
