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
package com.pb.common.daf;

import java.io.IOException;
import java.io.InputStream;

/**
 * MODIFIED ByteArrayInputStream
 *
 * 1. Added new methods (see bottom)
 * 2. Made methods un-synchronized.
 *
 * A <code>ByteArrayInputStream</code> contains
 * an internal buffer that contains bytes that
 * may be read from the stream. An internal
 * counter keeps track of the next byte to
 * be supplied by the <code>read</code> method.
 *
 * @author  Arthur van Hoff
 * @version 1.35, 02/02/00
 * @see     java.io.StringBufferInputStream
 * @since   JDK1.0
 */
public
class DAFByteArrayInputStream extends InputStream {

    /**
     * A flag that is set to true when this stream is closed.
     */
    private boolean isClosed = false;

    /**
     * An array of bytes that was provided
     * by the creator of the stream. Elements <code>buf[0]</code>
     * through <code>buf[count-1]</code> are the
     * only bytes that can ever be read from the
     * stream;  element <code>buf[pos]</code> is
     * the next byte to be read.
     */
    protected byte buf[];

    /**
     * The index of the next character to read from the input stream buffer.
     * This value should always be nonnegative
     * and not larger than the value of <code>count</code>.
     * The next byte to be read from the input stream buffer
     * will be <code>buf[pos]</code>.
     */
    protected int pos;

    /**
     * The currently marked position in the stream.
     * ByteArrayInputStream objects are marked at position zero by
     * default when constructed.  They may be marked at another
     * position within the buffer by the <code>mark()</code> method.
     * The current buffer position is set to this point by the
     * <code>reset()</code> method.
     *
     * @since   JDK1.1
     */
    protected int mark = 0;

    /**
     * The index one greater than the last valid character in the input
     * stream buffer.
     * This value should always be nonnegative
     * and not larger than the length of <code>buf</code>.
     * It  is one greater than the position of
     * the last byte within <code>buf</code> that
     * can ever be read  from the input stream buffer.
     */
    protected int count;

    /**
     * Creates a <code>ByteArrayInputStream</code>
     * so that it  uses <code>buf</code> as its
     * buffer array.
     * The buffer array is not copied.
     * The initial value of <code>pos</code>
     * is <code>0</code> and the initial value
     * of  <code>count</code> is the length of
     * <code>buf</code>.
     *
     * @param   buf   the input buffer.
     */
    public DAFByteArrayInputStream(byte buf[]) {
	    this.buf = buf;
        this.pos = 0;
	    this.count = buf.length;
    }

    /**
     * Creates <code>ByteArrayInputStream</code>
     * that uses <code>buf</code> as its
     * buffer array. The initial value of <code>pos</code>
     * is <code>offset</code> and the initial value
     * of <code>count</code> is <code>offset+len</code>.
     * The buffer array is not copied.
     * <p>
     * Note that if bytes are simply read from
     * the resulting input stream, elements <code>buf[pos]</code>
     * through <code>buf[pos+len-1]</code> will
     * be read; however, if a <code>reset</code>
     * operation  is performed, then bytes <code>buf[0]</code>
     * through b<code>uf[pos-1]</code> will then
     * become available for input.
     *
     * @param   buf      the input buffer.
     * @param   offset   the offset in the buffer of the first byte to read.
     * @param   length   the maximum number of bytes to read from the buffer.
     */
    public DAFByteArrayInputStream(byte buf[], int offset, int length) {
	this.buf = buf;
        this.pos = offset;
	this.count = Math.min(offset + length, buf.length);
        this.mark = offset;
    }

    /**
     * Reads the next byte of data from this input stream. The value
     * byte is returned as an <code>int</code> in the range
     * <code>0</code> to <code>255</code>. If no byte is available
     * because the end of the stream has been reached, the value
     * <code>-1</code> is returned.
     * <p>
     * This <code>read</code> method
     * cannot block.
     *
     * @return  the next byte of data, or <code>-1</code> if the end of the
     *          stream has been reached.
     */
    public int read() {
	ensureOpen();
	return (pos < count) ? (buf[pos++] & 0xff) : -1;
    }

    /**
     * Reads up to <code>len</code> bytes of data into an array of bytes
     * from this input stream.
     * If <code>pos</code> equals <code>count</code>,
     * then <code>-1</code> is returned to indicate
     * end of file. Otherwise, the  number <code>k</code>
     * of bytes read is equal to the smaller of
     * <code>len</code> and <code>count-pos</code>.
     * If <code>k</code> is positive, then bytes
     * <code>buf[pos]</code> through <code>buf[pos+k-1]</code>
     * are copied into <code>b[off]</code>  through
     * <code>b[off+k-1]</code> in the manner performed
     * by <code>System.arraycopy</code>. The
     * value <code>k</code> is added into <code>pos</code>
     * and <code>k</code> is returned.
     * <p>
     * This <code>read</code> method cannot block.
     *
     * @param   b     the buffer into which the data is read.
     * @param   off   the start offset of the data.
     * @param   len   the maximum number of bytes read.
     * @return  the total number of bytes read into the buffer, or
     *          <code>-1</code> if there is no more data because the end of
     *          the stream has been reached.
     */
    public int read(byte b[], int off, int len) {
	ensureOpen();
	if (b == null) {
	    throw new NullPointerException();
	} else if ((off < 0) || (off > b.length) || (len < 0) ||
		   ((off + len) > b.length) || ((off + len) < 0)) {
	    throw new IndexOutOfBoundsException();
	}
	if (pos >= count) {
	    return -1;
	}
	if (pos + len > count) {
	    len = count - pos;
	}
	if (len <= 0) {
	    return 0;
	}
	System.arraycopy(buf, pos, b, off, len);
	pos += len;
	return len;
    }

    /**
     * Skips <code>n</code> bytes of input from this input stream. Fewer
     * bytes might be skipped if the end of the input stream is reached.
     * The actual number <code>k</code>
     * of bytes to be skipped is equal to the smaller
     * of <code>n</code> and  <code>count-pos</code>.
     * The value <code>k</code> is added into <code>pos</code>
     * and <code>k</code> is returned.
     *
     * @param   n   the number of bytes to be skipped.
     * @return  the actual number of bytes skipped.
     */
    public long skip(long n) {
	ensureOpen();
	if (pos + n > count) {
	    n = count - pos;
	}
	if (n < 0) {
	    return 0;
	}
	pos += n;
	return n;
    }

    /**
     * Returns the number of bytes that can be read from this input
     * stream without blocking.
     * The value returned is
     * <code>count&nbsp;- pos</code>,
     * which is the number of bytes remaining to be read from the input buffer.
     *
     * @return  the number of bytes that can be read from the input stream
     *          without blocking.
     */
    public int available() {
	ensureOpen();
	return count - pos;
    }

    /**
     * Tests if ByteArrayInputStream supports mark/reset.
     *
     * @since   JDK1.1
     */
    public boolean markSupported() {
	return true;
    }

    /**
     * Set the current marked position in the stream.
     * ByteArrayInputStream objects are marked at position zero by
     * default when constructed.  They may be marked at another
     * position within the buffer by this method.
     *
     * @since   JDK1.1
     */
    public void mark(int readAheadLimit) {
	ensureOpen();
	mark = pos;
    }

    /**
     * Resets the buffer to the marked position.  The marked position
     * is the beginning unless another position was marked.
     * The value of <code>pos</code> is set to 0.
     */
    public void reset() {
	ensureOpen();
	pos = mark;
    }

    /**
     * Closes this input stream and releases any system resources
     * associated with the stream.
     * <p>
     */
    public void close() throws IOException {
	isClosed = true;
    }

    /** Check to make sure that the stream has not been closed */
    private void ensureOpen() {
        /* This method does nothing for now.  Once we add throws clauses
	 * to the I/O methods in this class, it will throw an IOException
	 * if the stream has been closed.
	 */
    }

    /**
     * ADDED: Takes a new buffer. Avoids the need to create a new object
     * just to read from a new buffer.
     * <p>
     *
     */
    public void setNewBuffer(byte buf[]) {
	    this.buf = buf;
        this.pos = 0;
	    this.count = buf.length;
    }

    /**
     * ADDED: No arguement constructor to support the setNewBuffer method.
     * This allows a empty buffer to be created. This allows the object to
     * be reused.
     *
     */
    public DAFByteArrayInputStream() {
	    this.buf = null;
        this.pos = 0;
	    this.count = 0;
    }
}
