/*
 * Copyright  2005 PB Consult Inc.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 *
 */
package com.pb.common.util;


import java.util.Iterator;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * This example implements a tokenizer that uses regular expressions. The use of 
 * this tokenizer is similar to the StringTokenizer class in that you use it like 
 * an iterator to extract the tokens.
 * 
 * CharSequence inputStr = "a 1 2 b c 3 4";
 * String patternStr = "[a-z]";
 * 
 * Set to false if only the tokens that match the pattern are to be returned.
 * If true, the text between matching tokens are also returned.
 * boolean returnDelims = true;
 *
 * Step 1. Create the tokenizer
 * Iterator tokenizer = new RETokenizer(inputStr, patternStr, returnDelims);
 * 
 * Step 2. Get the tokens (and delimiters)
 * for (; tokenizer.hasNext(); ) {
 *     String tokenOrDelim = (String)tokenizer.next();
 * }
 * 
 * "", "a", " 1 2 ", "b", " ", "c"
 * 
 */

class RETokenizer implements Iterator {
    // Holds the original input to search for tokens
    private CharSequence input;

    // Used to find tokens
    private Matcher matcher;

    // If true, the String between tokens are returned
    private boolean returnDelims;

    // The current delimiter value. If non-null, should be returned
    // at the next call to next()
    private String delim;

    // The current matched value. If non-null and delim=null,
    // should be returned at the next call to next()
    private String match;

    // The value of matcher.end() from the last successful match.
    private int lastEnd = 0;

    // patternStr is a regular expression pattern that identifies tokens.
    // If returnDelims delim is false, only those tokens that match the
    // pattern are returned. If returnDelims true, the text between
    // matching tokens are also returned. If returnDelims is true, the
    // tokens are returned in the following sequence - delimiter, token,
    // delimiter, token, etc. Tokens can never be empty but delimiters might
    // be empty (empty string).
    public RETokenizer(CharSequence input, String patternStr, boolean returnDelims) {
        // Save values
        this.input = input;
        this.returnDelims = returnDelims;

        // Compile pattern and prepare input
        Pattern pattern = Pattern.compile(patternStr);
        matcher = pattern.matcher(input);
    }

    // Returns true if there are more tokens or delimiters.
    public boolean hasNext() {
        if (matcher == null) {
            return false;
        }
        if (delim != null || match != null) {
            return true;
        }
        if (matcher.find()) {
            if (returnDelims) {
                delim = input.subSequence(lastEnd, matcher.start()).toString();
            }
            match = matcher.group();
            lastEnd = matcher.end();
        } else if (returnDelims && lastEnd < input.length()) {
            delim = input.subSequence(lastEnd, input.length()).toString();
            lastEnd = input.length();

            // Need to remove the matcher since it appears to automatically
            // reset itself once it reaches the end.
            matcher = null;
        }
        return delim != null || match != null;
    }

    // Returns the next token (or delimiter if returnDelims is true).
    public Object next() {
        String result = null;

        if (delim != null) {
            result = delim;
            delim = null;
        } else if (match != null) {
            result = match;
            match = null;
        }
        return result;
    }

    // Returns true if the call to next() will return a token rather
    // than a delimiter.
    public boolean isNextToken() {
        return delim == null && match != null;
    }

    // Not supported.
    public void remove() {
        throw new UnsupportedOperationException();
    }
}
