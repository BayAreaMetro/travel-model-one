To build, install apache ant (https://ant.apache.org/)

Compile thusly from within this directory (core), substituting the appropriate `JAVA_HOME` as appropriate:

```dosbatch
set REPOSITORY_DIR=%CD%
set JAVA_HOME=C:\Program Files\Java\jdk1.8.0_181
ant -Dbasedir=%REPOSITORY_DIR%\projects\mtc -buildfile build_mtc.xml
```
