package com.pb.models.utils;

import org.apache.log4j.Logger;

/**
 * The {@code StatusLogger} class allows users to log special messages in a standardized manner which can be read by
 * status logger clients.  It allows status to be reported using text, graph, or histogram.  The status is just text,
 * but the formatting is standardized so that a program reading it will be able to parse it consistently to produce
 * client-side messages and/or graphics.
 *
 * @version 1.0 Nov 16, 2007 - 9:34:32 AM
 * @author crf
 */
public class StatusLogger {
    private static Logger statusLogger = Logger.getLogger("status");

    private static void logStatus(String statusMessage) {
        statusLogger.info(statusMessage);
    }

    /**
     * Log a text status message. This consists of a text message, and a title for the status entry. As the logger
     * semicolon delimits its message (for whatever processor may use it), semicolons should not be used in any of the
     * arguments in the message.
     *
     * @param module
     *        The module logging this message.  Should be in the form <code>module.submodule.subsubmodule</code>(etc.).
     *        An example would be <code>pt.ld</code>
     *
     * @param title
     *        The title to use for this status entry.
     *
     * @param text
     *        The status message to log.
     */
    public static void logText(String module, String title,String text) {
        logStatus(module + ".status.text;" + title + ";" + text);
    }

    /**
     * Convenience method to log a text status message with a default title.  The title is formed by taking the first
     * part of the module name (the text up to the first dot (".")), capitalizing it, and appending " Status" to it.
     *
     * @param module
     *        The module logging this message.  Should be in the form <code>module.submodule.subsubmodule</code>(etc.).
     *        An example would be <code>pt.ld</code>
     *
     * @param text
     *        The status message to log.
     */
    public static void logText(String module, String text) {
        int dotIndex = module.indexOf('.');
        String moduleTitle = dotIndex > -1 ? module.substring(0,dotIndex).toUpperCase() : module.toUpperCase();
        logText(module,moduleTitle + " Status",text);
    }

    /**
     * Log a histogram status message.  A histogram message can be looked at as an "amount complete" gauge; it essentially
     * reports how much has been completed, and how much will have been completed when the model/module is finished.  As
     * the logger semicolon delimits its message (for whatever processor may use it), semicolons should not be used in
     * any of the arguments in the message.
     *
     * @param module
     *        The module logging this message.  Should be in the form <code>module.submodule.subsubmodule</code>(etc.).
     *        An example would be <code>pt.ld</code>
     *
     * @param title
     *        The title to use for this status entry.
     *
     * @param goal
     *        The point at which the model/module will be finished.
     *
     * @param currentPoint
     *        The current point.
     *
     * @param xAxisLabel
     *        The label to use for the histogram's x-axis.
     *
     * @param yAxisLabel
     *        The label to use for the histogram's y-axis.
     */
    public static void logHistogram(String module, String title, double goal, double currentPoint, String xAxisLabel, String yAxisLabel) {
        logStatus(module + ".status.histo;" + title + ";" + goal + ";" + currentPoint + ";" + xAxisLabel + ";" + yAxisLabel);
    }

    /**
     * Log a graph status message. This consists primarily of a pair of points (x,y) representing the current status of
     * the model/module.  A collection of these points could be read by the processor and graphed to show both the
     * current status as well as its progression. As the logger semicolon delimits its message (for whatever processor
     * may use it), semicolons should not be used in any of the arguments in the message.
     *
     * @param module
     *        The module logging this message.  Should be in the form <code>module.submodule.subsubmodule</code>(etc.).
     *        An example would be <code>pt.ld</code>
     *
     * @param title
     *        The title to use for this status entry.
     *
     * @param xPoint
     *        The x coordinate of the point to be graphed.
     *
     * @param yPoint
     *        The y coordinate of the point to be graphed.
     *
     * @param xAxisLabel
     *        The label to use for the histogram's x-axis.
     *
     * @param yAxisLabel
     *        The label to use for the histogram's y-axis.
     */
    public static void logGraph(String module, String title, double xPoint, double yPoint, String xAxisLabel, String yAxisLabel) {
        logStatus(module + ".status.graph;" + title + ";" + xPoint + ";" + yPoint + ";" + xAxisLabel + ";" + yAxisLabel);
    }
}
