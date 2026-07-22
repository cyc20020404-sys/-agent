package com.sky.dto;

import lombok.Data;

import java.io.Serializable;

@Data
public class H5LoginDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    private String phone;
    private String password;
}