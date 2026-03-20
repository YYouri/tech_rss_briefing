@echo off
chcp 65001
echo ================================================
echo  서드파티 jar 다운로드
echo ================================================

set DEST=C:\eclipse-thirdparty
if not exist %DEST% mkdir %DEST%

echo 시작: %date% %time%

:: Logback
curl -L -o %DEST%\ch.qos.logback.classic_1.0.7.jar https://repo1.maven.org/maven2/ch/qos/logback/logback-classic/1.0.7/logback-classic-1.0.7.jar
curl -L -o %DEST%\ch.qos.logback.core_1.0.7.jar https://repo1.maven.org/maven2/ch/qos/logback/logback-core/1.0.7/logback-core-1.0.7.jar

:: SLF4J
curl -L -o %DEST%\org.slf4j.api_1.7.2.jar https://repo1.maven.org/maven2/org/slf4j/slf4j-api/1.7.2/slf4j-api-1.7.2.jar
curl -L -o %DEST%\org.slf4j.impl.log4j12_1.7.2.jar https://repo1.maven.org/maven2/org/slf4j/slf4j-log4j12/1.7.2/slf4j-log4j12-1.7.2.jar

:: Google
curl -L -o %DEST%\com.google.gson_2.2.4.jar https://repo1.maven.org/maven2/com/google/code/gson/gson/2.2.4/gson-2.2.4.jar
curl -L -o %DEST%\com.google.guava_15.0.0.jar https://repo1.maven.org/maven2/com/google/guava/guava/15.0/guava-15.0.jar
curl -L -o %DEST%\com.google.inject_3.0.0.jar https://repo1.maven.org/maven2/com/google/inject/guice/3.0/guice-3.0.jar
curl -L -o %DEST%\com.google.inject.multibindings_3.0.0.jar https://repo1.maven.org/maven2/com/google/inject/extensions/guice-multibindings/3.0/guice-multibindings-3.0.jar

:: Jackson
curl -L -o %DEST%\jackson-core-2.5.0.jar https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-core/2.5.0/jackson-core-2.5.0.jar
curl -L -o %DEST%\jackson-databind-2.5.4.jar https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-databind/2.5.4/jackson-databind-2.5.4.jar
curl -L -o %DEST%\jackson-annotations-2.5.0.jar https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-annotations/2.5.0/jackson-annotations-2.5.0.jar

:: Apache Commons
curl -L -o %DEST%\commons-dbcp2-2.1.1.jar https://repo1.maven.org/maven2/org/apache/commons/commons-dbcp2/2.1.1/commons-dbcp2-2.1.1.jar
curl -L -o %DEST%\commons-pool2-2.4.2.jar https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.4.2/commons-pool2-2.4.2.jar
curl -L -o %DEST%\org.apache.commons.cli_1.2.jar https://repo1.maven.org/maven2/commons-cli/commons-cli/1.2/commons-cli-1.2.jar
curl -L -o %DEST%\org.apache.commons.codec_1.6.jar https://repo1.maven.org/maven2/commons-codec/commons-codec/1.6/commons-codec-1.6.jar
curl -L -o %DEST%\org.apache.commons.collections_3.2.2.jar https://repo1.maven.org/maven2/commons-collections/commons-collections/3.2.2/commons-collections-3.2.2.jar
curl -L -o %DEST%\org.apache.commons.compress_1.6.jar https://repo1.maven.org/maven2/org/apache/commons/commons-compress/1.6/commons-compress-1.6.jar
curl -L -o %DEST%\org.apache.commons.httpclient_3.1.jar https://repo1.maven.org/maven2/commons-httpclient/commons-httpclient/3.1/commons-httpclient-3.1.jar
curl -L -o %DEST%\org.apache.commons.io_2.2.jar https://repo1.maven.org/maven2/commons-io/commons-io/2.2/commons-io-2.2.jar
curl -L -o %DEST%\org.apache.commons.lang_2.6.jar https://repo1.maven.org/maven2/commons-lang/commons-lang/2.6/commons-lang-2.6.jar
curl -L -o %DEST%\org.apache.commons.lang3_3.1.jar https://repo1.maven.org/maven2/org/apache/commons/commons-lang3/3.1/commons-lang3-3.1.jar
curl -L -o %DEST%\org.apache.commons.logging_1.1.1.jar https://repo1.maven.org/maven2/commons-logging/commons-logging/1.1.1/commons-logging-1.1.1.jar
curl -L -o %DEST%\org.apache.commons.math_2.1.jar https://repo1.maven.org/maven2/org/apache/commons/commons-math/2.1/commons-math-2.1.jar
curl -L -o %DEST%\org.apache.commons.net_3.2.jar https://repo1.maven.org/maven2/commons-net/commons-net/3.2/commons-net-3.2.jar
curl -L -o %DEST%\org.apache.commons.pool_1.6.jar https://repo1.maven.org/maven2/commons-pool/commons-pool/1.6/commons-pool-1.6.jar

:: Apache HTTP
curl -L -o %DEST%\org.apache.httpcomponents.httpclient_4.3.6.jar https://repo1.maven.org/maven2/org/apache/httpcomponents/httpclient/4.3.6/httpclient-4.3.6.jar
curl -L -o %DEST%\org.apache.httpcomponents.httpcore_4.3.3.jar https://repo1.maven.org/maven2/org/apache/httpcomponents/httpcore/4.3.3/httpcore-4.3.3.jar

:: Apache 기타
curl -L -o %DEST%\org.apache.log4j_1.2.15.jar https://repo1.maven.org/maven2/log4j/log4j/1.2.15/log4j-1.2.15.jar
curl -L -o %DEST%\org.apache.lucene.core_3.5.0.jar https://repo1.maven.org/maven2/org/apache/lucene/lucene-core/3.5.0/lucene-core-3.5.0.jar
curl -L -o %DEST%\org.apache.lucene.analysis_3.5.0.jar https://repo1.maven.org/maven2/org/apache/lucene/lucene-analyzers/3.5.0/lucene-analyzers-3.5.0.jar
curl -L -o %DEST%\org.apache.velocity_1.5.jar https://repo1.maven.org/maven2/org/apache/velocity/velocity/1.5/velocity-1.5.jar
curl -L -o %DEST%\velocity-1.7.jar https://repo1.maven.org/maven2/org/apache/velocity/velocity/1.7/velocity-1.7.jar

:: Derby
curl -L -o %DEST%\derby_10.10.jar https://repo1.maven.org/maven2/org/apache/derby/derby/10.10.2.0/derby-10.10.2.0.jar

:: ANTLR
curl -L -o %DEST%\org.antlr.runtime_3.2.0.jar https://repo1.maven.org/maven2/org/antlr/antlr-runtime/3.2/antlr-runtime-3.2.jar

:: 기타
curl -L -o %DEST%\org.h2_1.3.168.jar https://repo1.maven.org/maven2/com/h2database/h2/1.3.168/h2-1.3.168.jar
curl -L -o %DEST%\org.jdom_1.1.1.jar https://repo1.maven.org/maven2/org/jdom/jdom/1.1.1/jdom-1.1.1.jar
curl -L -o %DEST%\org.jsoup_1.7.2.jar https://repo1.maven.org/maven2/org/jsoup/jsoup/1.7.2/jsoup-1.7.2.jar
curl -L -o %DEST%\org.mozilla.javascript_1.7.4.jar https://repo1.maven.org/maven2/org/mozilla/rhino/1.7.4/rhino-1.7.4.jar
curl -L -o %DEST%\org.objectweb.asm_5.0.1.jar https://repo1.maven.org/maven2/org/ow2/asm/asm/5.0.1/asm-5.0.1.jar
curl -L -o %DEST%\com.ibm.icu_54.1.1.jar https://repo1.maven.org/maven2/com/ibm/icu/icu4j/54.1.1/icu4j-54.1.1.jar
curl -L -o %DEST%\com.jcraft.jsch_0.1.53.jar https://repo1.maven.org/maven2/com/jcraft/jsch/0.1.53/jsch-0.1.53.jar

echo.
echo ================================================
echo  완료: %date% %time%
echo  저장위치: %DEST%
echo ================================================
pause
