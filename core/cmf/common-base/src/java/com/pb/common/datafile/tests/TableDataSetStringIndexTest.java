package com.pb.common.datafile.tests;

import org.junit.Test;
import org.junit.Before;
import static org.junit.Assert.*;
import com.pb.common.datafile.TableDataSet;

import java.util.Random;

/**
 * @author crf <br/>
 *         Started: May 31, 2009 2:15:54 PM
 */
public class TableDataSetStringIndexTest {

    private static final Random random = new Random();

    private final float[] floatColumn = {1,2,3,4};
    private final String[] stringColumn = {"a","b","c","d"};
    private final String uniqueExtraString = "f";
    private final String unusedString = "0";
    private final String[] booleanColumn = {"true","false","true","false"};
    private final String floatColumnLabel = "float";
    private final String stringColumnLabel = "String";
    private final String booleanColumnLabel = "boolean";

    private TableDataSet table;
    private int floatColumnNumber;
    private int stringColumnNumber;
    private int booleanColumnNumber;

    private TableDataSet getTestDataSet() {
        TableDataSet t = new TableDataSet();
        float[] fc = new float[floatColumn.length];
        String[] sc = new String[stringColumn.length];
        String[] bc = new String[booleanColumn.length];
        System.arraycopy(floatColumn,0,fc,0,fc.length);
        System.arraycopy(stringColumn,0,sc,0,sc.length);
        System.arraycopy(booleanColumn,0,bc,0,bc.length);
        t.appendColumn(fc,floatColumnLabel);
        t.appendColumn(sc,stringColumnLabel);
        t.appendColumn(bc,booleanColumnLabel);
        floatColumnNumber = 1;
        stringColumnNumber = 2;
        booleanColumnNumber = 3;
        return t;
    }

    @Before
    public void before() {
        table = getTestDataSet();
    }

    @Test(expected=RuntimeException.class)
    public void testBuildIndexOnNonStringColumn() {
        table.buildStringIndex(floatColumnNumber);
    }

    @Test(expected=IllegalStateException.class)
    public void testBuildIndexRepeatedValues() {
        table.setStringValueAt(2,stringColumnNumber,table.getStringValueAt(1,stringColumnNumber));
        table.buildStringIndex(stringColumnNumber);
    }

    @Test
    public void testGetRowNumber() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(stringColumn.length);
        assertEquals(row,table.getStringIndexedRowNumber(stringColumn[row]));
    }

    @Test(expected=IllegalStateException.class)
    public void testGetRowNumberNoIndex() {
        table.getStringIndexedRowNumber(stringColumn[0]);
    }

    @Test(expected=IllegalStateException.class)
    public void testGetRowNumberIndexDirty() {
        table.buildStringIndex(stringColumnNumber);
        table.setStringValueAt(2,stringColumnNumber,uniqueExtraString);
        table.getStringIndexedRowNumber(stringColumn[0]);
    }

    @Test(expected=IllegalArgumentException.class)
    public void testGetRowNumberNoIndexValue() {
        table.buildStringIndex(stringColumnNumber);
        table.getStringIndexedRowNumber(unusedString);
    }

    @Test
    public void testGetStringValue() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(stringColumn.length);
        assertEquals(stringColumn[row],table.getStringIndexedStringValueAt(stringColumn[row],stringColumnNumber));
    }

    @Test(expected=IllegalStateException.class)
    public void testGetStringValueNoIndex() {
        table.getStringIndexedStringValueAt(stringColumn[0],stringColumnNumber);
    }

    @Test(expected=IllegalStateException.class)
    public void testGetStringValueIndexDirty() {
        table.buildStringIndex(stringColumnNumber);
        table.setStringValueAt(2,stringColumnNumber,uniqueExtraString);
        table.getStringIndexedStringValueAt(stringColumn[0],stringColumnNumber);
    }

    @Test(expected=IllegalArgumentException.class)
    public void testGetStringValueNoIndexValue() {
        table.buildStringIndex(stringColumnNumber);
        table.getStringIndexedStringValueAt(unusedString,stringColumnNumber);
    }

    @Test(expected=IndexOutOfBoundsException.class)
    public void testGetStringValueColumnTooLow() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(stringColumn.length);
        table.getStringIndexedStringValueAt(stringColumn[row],0);
    }

    @Test(expected=IndexOutOfBoundsException.class)
    public void testGetStringValueColumnTooHigh() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(stringColumn.length);
        table.getStringIndexedStringValueAt(stringColumn[row],table.getColumnCount()+1);
    }

    @Test
    public void testGetStringValueColumnLabel() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(stringColumn.length);
        assertEquals(stringColumn[row],table.getStringIndexedStringValueAt(stringColumn[row],stringColumnLabel));
    }

    @Test(expected=IllegalStateException.class)
    public void testGetStringValueColumnLabelNoIndex() {
        table.getStringIndexedStringValueAt(stringColumn[0],stringColumnLabel);
    }

    @Test(expected=IllegalStateException.class)
    public void testGetStringValueColumnLabelIndexDirty() {
        table.buildStringIndex(stringColumnNumber);
        table.setStringValueAt(2,stringColumnNumber,uniqueExtraString);
        table.getStringIndexedStringValueAt(stringColumn[0],stringColumnLabel);
    }

    @Test(expected=IllegalArgumentException.class)
    public void testGetStringValueColumnLabelNoIndexValue() {
        table.buildStringIndex(stringColumnNumber);
        table.getStringIndexedStringValueAt(unusedString,stringColumnLabel);
    }

    @Test(expected=RuntimeException.class)
    public void testGetStringValueColumnLabelInvalid() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(stringColumn.length);
        table.getStringIndexedStringValueAt(stringColumn[row],"not_a_column");
    }



    @Test
    public void testGetBooleanValue() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(booleanColumn.length);
        assertEquals(Boolean.parseBoolean(booleanColumn[row]),table.getStringIndexedBooleanValueAt(stringColumn[row],booleanColumnNumber));
    }

    @Test(expected=IllegalStateException.class)
    public void testGetBooleanValueNoIndex() {
        table.getStringIndexedBooleanValueAt(stringColumn[0],booleanColumnNumber);
    }

    @Test(expected=IllegalStateException.class)
    public void testGetBooleanValueIndexDirty() {
        table.buildStringIndex(stringColumnNumber);
        table.setStringValueAt(2,stringColumnNumber,uniqueExtraString);
        table.getStringIndexedBooleanValueAt(stringColumn[0],booleanColumnNumber);
    }

    @Test(expected=IllegalArgumentException.class)
    public void testGetBooleanValueNoIndexValue() {
        table.buildStringIndex(stringColumnNumber);
        table.getStringIndexedBooleanValueAt(unusedString,booleanColumnNumber);
    }

    @Test(expected=IndexOutOfBoundsException.class)
    public void testGetBooleanValueColumnTooLow() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(booleanColumn.length);
        table.getStringIndexedBooleanValueAt(stringColumn[row],0);
    }

    @Test(expected=IndexOutOfBoundsException.class)
    public void testGetBooleanValueColumnTooHigh() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(booleanColumn.length);
        table.getStringIndexedBooleanValueAt(stringColumn[row],table.getColumnCount()+1);
    }

    @Test(expected=RuntimeException.class)
    public void testGetBooleanValueNonBooleanColumn() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(booleanColumn.length);
        table.getStringIndexedBooleanValueAt(stringColumn[row],floatColumnNumber);
    }

    @Test
    public void testGetBooleanValueColumnLabel() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(booleanColumn.length);
        assertEquals(Boolean.parseBoolean(booleanColumn[row]),table.getStringIndexedBooleanValueAt(stringColumn[row],booleanColumnLabel));
    }

    @Test(expected=IllegalStateException.class)
    public void testGetBooleanValueColumnLabelNoIndex() {
        table.getStringIndexedBooleanValueAt(stringColumn[0],booleanColumnLabel);
    }

    @Test(expected=IllegalStateException.class)
    public void testGetBooleanValueColumnLabelIndexDirty() {
        table.buildStringIndex(stringColumnNumber);
        table.setStringValueAt(2,stringColumnNumber,uniqueExtraString);
        table.getStringIndexedBooleanValueAt(stringColumn[0],booleanColumnLabel);
    }

    @Test(expected=IllegalArgumentException.class)
    public void testGetBooleanValueColumnLabelNoIndexValue() {
        table.buildStringIndex(stringColumnNumber);
        table.getStringIndexedBooleanValueAt(unusedString,booleanColumnLabel);
    }

    @Test(expected=RuntimeException.class)
    public void testGetBooleanValueColumnLabelInvalid() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(booleanColumn.length);
        table.getStringIndexedBooleanValueAt(stringColumn[row],"not_a_column");
    }

    @Test(expected=RuntimeException.class)
    public void testGetBooleanValueColumnLabelNonbooleanColumn() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(booleanColumn.length);
        table.getStringIndexedBooleanValueAt(stringColumn[row],floatColumnLabel);
    }



    @Test
    public void testGetFloatValue() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(floatColumn.length);
        assertEquals(floatColumn[row],table.getStringIndexedValueAt(stringColumn[row],floatColumnNumber));
    }

    @Test(expected=IllegalStateException.class)
    public void testGetFloatValueNoIndex() {
        table.getStringIndexedValueAt(stringColumn[0],floatColumnNumber);
    }

    @Test(expected=IllegalStateException.class)
    public void testGetFloatValueIndexDirty() {
        table.buildStringIndex(stringColumnNumber);
        table.setStringValueAt(2,stringColumnNumber,uniqueExtraString);
        table.getStringIndexedValueAt(stringColumn[0],floatColumnNumber);
    }

    @Test(expected=IllegalArgumentException.class)
    public void testGetFloatValueNoIndexValue() {
        table.buildStringIndex(stringColumnNumber);
        table.getStringIndexedValueAt(unusedString,floatColumnNumber);
    }

    @Test(expected=IndexOutOfBoundsException.class)
    public void testGetFloatValueColumnTooLow() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(floatColumn.length);
        table.getStringIndexedValueAt(stringColumn[row],0);
    }

    @Test(expected=IndexOutOfBoundsException.class)
    public void testGetFloatValueColumnTooHigh() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(floatColumn.length);
        table.getStringIndexedValueAt(stringColumn[row],table.getColumnCount()+1);
    }

    @Test(expected=RuntimeException.class)
    public void testGetFloatValueNonFloatColumn() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(floatColumn.length);
        table.getStringIndexedValueAt(stringColumn[row],stringColumnNumber);
    }

    @Test
    public void testGetFloatValueColumnLabel() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(floatColumn.length);
        assertEquals(floatColumn[row],table.getStringIndexedValueAt(stringColumn[row],floatColumnLabel));
    }

    @Test(expected=IllegalStateException.class)
    public void testGetFloatValueColumnLabelNoIndex() {
        table.getStringIndexedValueAt(stringColumn[0],floatColumnLabel);
    }

    @Test(expected=IllegalStateException.class)
    public void testGetFloatValueColumnLabelIndexDirty() {
        table.buildStringIndex(stringColumnNumber);
        table.setStringValueAt(2,stringColumnNumber,uniqueExtraString);
        table.getStringIndexedValueAt(stringColumn[0],floatColumnLabel);
    }

    @Test(expected=IllegalArgumentException.class)
    public void testGetFloatValueColumnLabelNoIndexValue() {
        table.buildStringIndex(stringColumnNumber);
        table.getStringIndexedValueAt(unusedString,floatColumnLabel);
    }

    @Test(expected=RuntimeException.class)
    public void testGetFloatValueColumnLabelInvalid() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(floatColumn.length);
        table.getStringIndexedValueAt(stringColumn[row],"not_a_column");
    }

    @Test(expected=RuntimeException.class)
    public void testGetFloatValueColumnLabelNonfloatColumn() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(floatColumn.length);        
        table.getStringIndexedValueAt(stringColumn[row],stringColumnLabel);
    }

    @Test
    public void testSetStringValue() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(stringColumn.length);
        String value = uniqueExtraString;
        table.setStringIndexedStringValueAt(stringColumn[row],stringColumnNumber,value);
        assertEquals(value,table.getStringValueAt(row+1,stringColumnNumber));
    }

    @Test(expected=IllegalStateException.class)
    public void testSetStringValueNoIndex() {
        table.setStringIndexedStringValueAt(stringColumn[0],stringColumnNumber,uniqueExtraString);
    }

    @Test(expected=IllegalStateException.class)
    public void testSetStringValueIndexDirty() {
        table.buildStringIndex(stringColumnNumber);
        table.setStringValueAt(2,stringColumnNumber,uniqueExtraString);
        table.setStringIndexedStringValueAt(stringColumn[0],stringColumnNumber,uniqueExtraString);
    }

    @Test(expected=IllegalArgumentException.class)
    public void testSetStringValueNoIndexValue() {
        table.buildStringIndex(stringColumnNumber);
        table.setStringIndexedStringValueAt(unusedString,stringColumnNumber,uniqueExtraString);
    }

    @Test(expected=IndexOutOfBoundsException.class)
    public void testSetStringValueColumnTooLow() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(stringColumn.length);
        table.setStringIndexedStringValueAt(stringColumn[row],0,uniqueExtraString);
    }

    @Test(expected=IndexOutOfBoundsException.class)
    public void testSetStringValueColumnTooHigh() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(stringColumn.length);
        table.setStringIndexedStringValueAt(stringColumn[row],table.getColumnCount()+1,uniqueExtraString);
    }

    @Test(expected=RuntimeException.class)
    public void testSetStringValueNonStringColumn() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(stringColumn.length);
        table.setStringIndexedStringValueAt(stringColumn[row],floatColumnNumber,uniqueExtraString);
    }

    @Test
    public void testSetStringValueColumnLabel() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(stringColumn.length);
        String value = uniqueExtraString;
        table.setStringIndexedStringValueAt(stringColumn[row],stringColumnLabel,value);
        assertEquals(value,table.getStringValueAt(row+1,stringColumnNumber));
    }

    @Test(expected=IllegalStateException.class)
    public void testSetStringValueColumnLabelNoIndex() {
        table.setStringIndexedStringValueAt(stringColumn[0],stringColumnLabel,uniqueExtraString);
    }

    @Test(expected=IllegalStateException.class)
    public void testSetStringValueColumnLabelIndexDirty() {
        table.buildStringIndex(stringColumnNumber);
        table.setStringValueAt(2,stringColumnNumber,uniqueExtraString);
        table.setStringIndexedStringValueAt(stringColumn[0],stringColumnLabel,uniqueExtraString);
    }

    @Test(expected=IllegalArgumentException.class)
    public void testSetStringValueColumnLabelNoIndexValue() {
        table.buildStringIndex(stringColumnNumber);
        table.setStringIndexedStringValueAt(unusedString,stringColumnLabel,uniqueExtraString);
    }

    @Test(expected=RuntimeException.class)
    public void testSetStringValueColumnLabelInvalid() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(stringColumn.length);
        table.setStringIndexedStringValueAt(stringColumn[row],"not_a_column",uniqueExtraString);
    }

    @Test(expected=RuntimeException.class)
    public void testSetStringValueColumnLabelNonstringColumn() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(stringColumn.length);
        table.setStringIndexedStringValueAt(stringColumn[row],floatColumnLabel,uniqueExtraString);
    }

    @Test
    public void testSetBooleanValue() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(booleanColumn.length);
        boolean value = random.nextBoolean();
        table.setStringIndexedBooleanValueAt(stringColumn[row],booleanColumnNumber,value);
        assertEquals(value,table.getBooleanValueAt(row+1,booleanColumnNumber));
    }

    @Test(expected=IllegalStateException.class)
    public void testSetBooleanValueNoIndex() {
        table.setStringIndexedBooleanValueAt(stringColumn[0],booleanColumnNumber,random.nextBoolean());
    }

    @Test(expected=IllegalStateException.class)
    public void testSetBooleanValueIndexDirty() {
        table.buildStringIndex(stringColumnNumber);
        table.setStringValueAt(2,stringColumnNumber,uniqueExtraString);
        table.setStringIndexedBooleanValueAt(stringColumn[0],booleanColumnNumber,random.nextBoolean());
    }

    @Test(expected=IllegalArgumentException.class)
    public void testSetBooleanValueNoIndexValue() {
        table.buildStringIndex(stringColumnNumber);
        table.setStringIndexedBooleanValueAt(unusedString,booleanColumnNumber,random.nextBoolean());
    }

    @Test(expected=IndexOutOfBoundsException.class)
    public void testSetBooleanValueColumnTooLow() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(booleanColumn.length);
        table.setStringIndexedBooleanValueAt(stringColumn[row],0,random.nextBoolean());
    }

    @Test(expected=IndexOutOfBoundsException.class)
    public void testSetBooleanValueColumnTooHigh() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(booleanColumn.length);
        table.setStringIndexedBooleanValueAt(stringColumn[row],table.getColumnCount()+1,random.nextBoolean());
    }

    @Test(expected=ClassCastException.class)
    public void testSetBooleanValueNonBooleanColumn() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(booleanColumn.length);
        table.setStringIndexedBooleanValueAt(stringColumn[row],floatColumnNumber,random.nextBoolean());
    }

    @Test
    public void testSetBooleanValueColumnLabel() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(booleanColumn.length);
        boolean value = random.nextBoolean();
        table.setStringIndexedBooleanValueAt(stringColumn[row],booleanColumnLabel,value);
        assertEquals(value,table.getBooleanValueAt(row+1,booleanColumnNumber));
    }

    @Test(expected=IllegalStateException.class)
    public void testSetBooleanValueColumnLabelNoIndex() {
        table.setStringIndexedBooleanValueAt(stringColumn[0],booleanColumnLabel,random.nextBoolean());
    }

    @Test(expected=IllegalStateException.class)
    public void testSetBooleanValueColumnLabelIndexDirty() {
        table.buildStringIndex(stringColumnNumber);
        table.setStringValueAt(2,stringColumnNumber,uniqueExtraString);
        table.setStringIndexedBooleanValueAt(stringColumn[0],booleanColumnLabel,random.nextBoolean());
    }

    @Test(expected=IllegalArgumentException.class)
    public void testSetBooleanValueColumnLabelNoIndexValue() {
        table.buildStringIndex(stringColumnNumber);
        table.setStringIndexedBooleanValueAt(unusedString,booleanColumnLabel,random.nextBoolean());
    }

    @Test(expected=RuntimeException.class)
    public void testSetBooleanValueColumnLabelInvalid() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(booleanColumn.length);
        table.setStringIndexedBooleanValueAt(stringColumn[row],"not_a_column",random.nextBoolean());
    }

    @Test(expected=ClassCastException.class)
    public void testSetBooleanValueColumnLabelNonbooleanColumn() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(booleanColumn.length);
        table.setStringIndexedBooleanValueAt(stringColumn[row],floatColumnLabel,random.nextBoolean());
    }

    @Test
    public void testSetFloatValue() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(floatColumn.length);
        float value = random.nextFloat();
        table.setStringIndexedValueAt(stringColumn[row],floatColumnNumber,value);
        assertEquals(value,table.getValueAt(row+1,floatColumnNumber));
    }

    @Test(expected=IllegalStateException.class)
    public void testSetFloatValueNoIndex() {
        table.setStringIndexedValueAt(stringColumn[0],floatColumnNumber,random.nextFloat());
    }

    @Test(expected=IllegalStateException.class)
    public void testSetFloatValueIndexDirty() {
        table.buildStringIndex(stringColumnNumber);
        table.setStringValueAt(2,stringColumnNumber,uniqueExtraString);
        table.setStringIndexedValueAt(stringColumn[0],floatColumnNumber,random.nextFloat());
    }

    @Test(expected=IllegalArgumentException.class)
    public void testSetFloatValueNoIndexValue() {
        table.buildStringIndex(stringColumnNumber);
        table.setStringIndexedValueAt(unusedString,floatColumnNumber,random.nextFloat());
    }

    @Test(expected=IndexOutOfBoundsException.class)
    public void testSetFloatValueColumnTooLow() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(floatColumn.length);
        table.setStringIndexedValueAt(stringColumn[row],0,random.nextFloat());
    }

    @Test(expected=IndexOutOfBoundsException.class)
    public void testSetFloatValueColumnTooHigh() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(floatColumn.length);
        table.setStringIndexedValueAt(stringColumn[row],table.getColumnCount()+1,random.nextFloat());
    }

    @Test(expected=RuntimeException.class)
    public void testSetFloatValueNonFloatColumn() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(floatColumn.length);
        table.setStringIndexedValueAt(stringColumn[row],stringColumnNumber,random.nextFloat());
    }

    @Test
    public void testSetFloatValueColumnLabel() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(floatColumn.length);
        float value = random.nextFloat();
        table.setStringIndexedValueAt(stringColumn[row],floatColumnLabel,value);
        assertEquals(value,table.getValueAt(row+1,floatColumnNumber));
    }

    @Test(expected=IllegalStateException.class)
    public void testSetFloatValueColumnLabelNoIndex() {
        table.setStringIndexedValueAt(stringColumn[0],floatColumnLabel,random.nextFloat());
    }

    @Test(expected=IllegalStateException.class)
    public void testSetFloatValueColumnLabelIndexDirty() {
        table.buildStringIndex(stringColumnNumber);
        table.setStringValueAt(2,stringColumnNumber,uniqueExtraString);
        table.setStringIndexedValueAt(stringColumn[0],floatColumnLabel,random.nextFloat());
    }

    @Test(expected=IllegalArgumentException.class)
    public void testSetFloatValueColumnLabelNoIndexValue() {
        table.buildStringIndex(stringColumnNumber);
        table.setStringIndexedValueAt(unusedString,floatColumnLabel,random.nextFloat());
    }

    @Test(expected=RuntimeException.class)
    public void testSetFloatValueColumnLabelInvalid() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(floatColumn.length);
        table.setStringIndexedValueAt(stringColumn[row],"not_a_column",random.nextFloat());
    }

    @Test(expected=RuntimeException.class)
    public void testSetFloatValueColumnLabelNonFloatColumn() {
        table.buildStringIndex(stringColumnNumber);
        int row = random.nextInt(floatColumn.length);
        table.setStringIndexedValueAt(stringColumn[row],stringColumnLabel,random.nextFloat());
    }
}
