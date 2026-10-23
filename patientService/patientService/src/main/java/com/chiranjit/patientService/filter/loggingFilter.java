package com.chiranjit.patientService.filter;

import org.springframework.stereotype.Component;

import jakarta.servlet.Filter;

import java.util.logging.Logger;


@Component 
public class loggingFilter implements Filter {
    private static final Logger logger = Logger.getLogger(loggingFilter.class.getName());

    @Override 
    public void doFilter(jakarta.servlet.ServletRequest request, jakarta.servlet.ServletResponse response, jakarta.servlet.FilterChain chain) throws java.io.IOException, jakarta.servlet.ServletException {
        
       logger.info("Request received at: " + new java.util.Date());
        chain.doFilter(request, response);
      logger.info("Response sent at: " + new java.util.Date());
       
    }


    
}
