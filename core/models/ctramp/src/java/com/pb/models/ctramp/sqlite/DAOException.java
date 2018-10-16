package com.pb.models.ctramp.sqlite;

public class DAOException extends RuntimeException
{
	static final long serialVersionUID = -1881205326938716446L;

	public DAOException(String message)
	{
		super(message);
	}

	public DAOException(Throwable cause)
	{
		super(cause);
	}

	public DAOException(String message, Throwable cause)
	{
		super(message, cause);
	}

}
