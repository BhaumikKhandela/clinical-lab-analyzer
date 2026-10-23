package com.chiranjit.authService.entity;

/**
 * What an account may do.
 *
 * Two roles, because that is what the service actually distinguishes: creating
 * other accounts, and everything else. Adding a third would mean finding a rule
 * that genuinely differs.
 */
public enum Role {

	/** May create and disable accounts, on top of everything a clinician can do. */
	ADMIN,

	/** May read and write patient records, reports, images and analyses. */
	CLINICIAN

}
