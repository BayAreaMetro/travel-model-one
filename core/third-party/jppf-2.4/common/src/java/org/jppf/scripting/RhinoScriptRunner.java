/*
 * JPPF.
 * Copyright (C) 2005-2010 JPPF Team.
 * http://www.jppf.org
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.jppf.scripting;

import java.util.*;

import org.mozilla.javascript.*;
import org.slf4j.*;

/**
 * Script runner wrapper around a Rhino script engine.
 * @author Laurent Cohen
 */
public class RhinoScriptRunner implements ScriptRunner
{
	/**
	 * Logger for this class.
	 */
	private static Logger log = LoggerFactory.getLogger(RhinoScriptRunner.class);

	/**
	 * Determines whether debug log statements are enabled.
	 */
	private static boolean debugEnabled = log.isDebugEnabled();
	/**
	 * Contains information about the scripts execution environment.
	 */
	private Context context = null;
	/**
	 * Contains information about global variables.
	 */
	private Scriptable scope = null;
	/**
	 * USed to collect error messages.
	 */
	private ErrorHandler errorHandler = new ErrorHandler();
	/**
	 * Mapping of Rhino scripts to their uuid.
	 */
	private static Map<String, Script> scriptMap = new HashMap<String, Script>();

	/**
	 * Initialize the Rhino environment.
	 */
	public RhinoScriptRunner()
	{
	}

	/**
	 * Evaluate the script specified as input and get the evaluation result.
	 * @param script a string containing the script to evaluate.
	 * @param variables a mapping of objects to add the scope of the script.
	 * @return the result of the evaluation as an object.
	 * @throws JPPFScriptingException if an error occurs while evaluating the script.
	 * @see org.jppf.scripting.ScriptRunner#evaluate(java.lang.String script, java.util.Map)
	 */
	public Object evaluate(String script, Map<String, Object> variables) throws JPPFScriptingException
	{
		return evaluate(null, script, variables);
	}

	/**
	 * Evaluate the script specified as input and get the evaluation result.
	 * @param scriptId - a unique identifer for the script, to be used if the engine generates compiled code
	 * which can be later retrieved through this id.
	 * @param script - a string containing the script to evaluate.
	 * @param variables - a mapping of objects to variable names, added within the scope of the script.
	 * @return the result of the evaluation as an object. The actual type of the result
	 * depends on the scripting engine that is used.
	 * @throws JPPFScriptingException if an error occurs while evaluating the script.
	 * @see org.jppf.scripting.ScriptRunner#evaluate(java.lang.String, java.lang.String, java.util.Map)
	 */
	public Object evaluate(String scriptId, String script, Map<String, Object> variables) throws JPPFScriptingException
	{
		init();
		errorHandler.errors.clear();
		Object result = null;
		for (Map.Entry<String, Object> entry: variables.entrySet())
		{
			Object wrapped = Context.javaToJS(entry.getValue(), scope);
			ScriptableObject.putProperty(scope, entry.getKey(), wrapped);
		}
		Script rhinoScript = null;
		if (scriptId != null) rhinoScript = scriptMap.get(scriptId);
		if (rhinoScript == null)
		{
			rhinoScript = context.compileString(script, "script", 1, null);
			if (scriptId != null) scriptMap.put(scriptId, rhinoScript);
		}
		try
		{
			//result = context.evaluateString(scope, script, "script", 1, null);
			result = rhinoScript.exec(context, scope);
		}
		catch(EvaluatorException e)
		{
			if (debugEnabled) log.debug(e.getMessage(), e);
		}
		finally
		{
			for (String name: variables.keySet()) ScriptableObject.deleteProperty(scope, name);
			cleanup();
		}
		if (!errorHandler.errors.isEmpty())
		{
			StringBuilder sb = new StringBuilder();
			for (String s: errorHandler.errors)
			{
				if (sb.length() > 0) sb.append("\n");
				sb.append(s);
			}
			sb.insert(0, "Errors occurred while executing the script:\n");
			throw new JPPFScriptingException(sb.toString());
		}
		return result;
	}

	/**
	 * Initialize the execution environment.
	 * @see org.jppf.scripting.ScriptRunner#init()
	 */
	public void init()
	{
		context = new ContextFactory().enterContext();
		//scope = context.initStandardObjects(null);
		scope = new ImporterTopLevel(context);
		context.setErrorReporter(errorHandler);
	}

	/**
	 * Perform cleanup after we're done using this script runner.
	 * @see org.jppf.scripting.ScriptRunner#cleanup()
	 */
	public void cleanup()
	{
		Context.exit();
	}

	/**
	 * Error handler for this script runner.
	 */
	public static class ErrorHandler implements ErrorReporter
	{
		/**
		 * Errors thrown during execution or translation of a script.
		 */
		public List<String> errors = new ArrayList<String>();

		/**
     * Report an error.
     * If execution has not yet begun, the JavaScript engine is free to
     * find additional errors rather than terminating the translation.
     * It will not execute a script that had errors, however.
     * @param message a String describing the error
     * @param sourceName a String describing the JavaScript source
     * where the error occured; typically a filename or URL
     * @param line the line number associated with the error
     * @param lineSource the text of the line (may be null)
     * @param lineOffset the offset into lineSource where problem was detected
		 * @see org.mozilla.javascript.ErrorReporter#error(java.lang.String, java.lang.String, int, java.lang.String, int)
		 */
		public void error(String message, String sourceName, int line, String lineSource, int lineOffset)
		{
			errors.add(makeErrorString(message, sourceName, line, lineSource, lineOffset));
		}

		/**
     * Report a warning.
     * @param message a String describing the warning
     * @param sourceName a String describing the JavaScript source
     * where the warning occured; typically a filename or URL
     * @param line the line number associated with the warning
     * @param lineSource the text of the line (may be null)
     * @param lineOffset the offset into lineSource where problem was detected
		 * @see org.mozilla.javascript.ErrorReporter#warning(java.lang.String, java.lang.String, int, java.lang.String, int)
		 */
		public void warning(String message, String sourceName, int line, String lineSource, int lineOffset)
		{
		}
	
		/**
     * Creates an EvaluatorException that may be thrown.
     * runtimeErrors, unlike errors, will always terminate the current script.
     * @param message a String describing the error
     * @param sourceName a String describing the JavaScript source
     * where the error occured; typically a filename or URL
     * @param line the line number associated with the error
     * @param lineSource the text of the line (may be null)
     * @param lineOffset the offset into lineSource where problem was detected
     * @return an EvaluatorException that will be thrown.
		 * @see org.mozilla.javascript.ErrorReporter#runtimeError(java.lang.String, java.lang.String, int, java.lang.String, int)
		 */
		public EvaluatorException runtimeError(String message, String sourceName, int line, String lineSource, int lineOffset)
		{
			String s = makeErrorString(message, sourceName, line, lineSource, lineOffset);
			errors.add(s);
			return new EvaluatorException(s);
		}

		/**
		 * Generate a single string form the parametrs of an error or warning.
     * @param message a String describing the warning
     * @param sourceName a String describing the JavaScript source
     * where the warning occured; typically a filename or URL
     * @param line the line number associated with the warning
     * @param lineSource the text of the line (may be null)
     * @param lineOffset the offset into lineSource where problem was detected
		 * @return a string containing the information about the error.
		 */
		private String makeErrorString(String message, String sourceName, int line, String lineSource, int lineOffset)
		{
			StringBuilder sb = new StringBuilder();
			sb.append(message).append(" at ").append(line).append(":").append(lineOffset).append(":\n");
			sb.append("Source = ").append(lineSource);
			return sb.toString();
		}
	}
}
