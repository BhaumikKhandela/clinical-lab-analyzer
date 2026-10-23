package com.chiranjit.authService.repository;

import com.chiranjit.authService.entity.AppUser;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface AppUserRepository extends JpaRepository<AppUser, UUID> {

	/** Callers lowercase before calling; the column holds lowercase only. */
	Optional<AppUser> findByUsername(String username);

	boolean existsByUsername(String username);

}
