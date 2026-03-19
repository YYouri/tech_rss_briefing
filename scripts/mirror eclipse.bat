@echo off
chcp 65001
echo ================================================
echo  Eclipse 2024-06 Plugin Mirror Download
echo ================================================

:: -----------------------------------------------
:: 설정 - 본인 환경에 맞게 수정
:: -----------------------------------------------
set ECLIPSE=C:\eclipse\eclipsec.exe
set DEST=C:\eclipse-mirror
set LOG=C:\eclipse-mirror\mirror.log

:: -----------------------------------------------
:: 폴더 생성
:: -----------------------------------------------
if not exist %DEST% mkdir %DEST%
if not exist %DEST%\2024-06 mkdir %DEST%\2024-06
if not exist %DEST%\egit mkdir %DEST%\egit
if not exist %DEST%\buildship mkdir %DEST%\buildship
if not exist %DEST%\mylyn mkdir %DEST%\mylyn
if not exist %DEST%\datatools mkdir %DEST%\datatools
if not exist %DEST%\svn mkdir %DEST%\svn
if not exist %DEST%\bytecodeoutline mkdir %DEST%\bytecodeoutline
if not exist %DEST%\thirdparty mkdir %DEST%\thirdparty

echo 시작시간: %date% %time% > %LOG%

:: -----------------------------------------------
:: 1. Eclipse 메인 (플랫폼/JDT/PDE/WTP/EMF 등)
:: -----------------------------------------------
echo.
echo [1/7] Eclipse 2024-06 메인 미러링 시작...
echo [1/7] Eclipse 메인 시작: %time% >> %LOG%

%ECLIPSE% -nosplash ^
  -application org.eclipse.equinox.p2.artifact.repository.mirrorApplication ^
  -source https://download.eclipse.org/releases/2024-06 ^
  -destination %DEST%\2024-06 ^
  -verbose >> %LOG% 2>&1

%ECLIPSE% -nosplash ^
  -application org.eclipse.equinox.p2.metadata.repository.mirrorApplication ^
  -source https://download.eclipse.org/releases/2024-06 ^
  -destination %DEST%\2024-06 ^
  -verbose >> %LOG% 2>&1

echo [1/7] Eclipse 메인 완료: %time% >> %LOG%
echo [1/7] 완료

:: -----------------------------------------------
:: 2. EGit
:: -----------------------------------------------
echo.
echo [2/7] EGit 미러링 시작...
echo [2/7] EGit 시작: %time% >> %LOG%

%ECLIPSE% -nosplash ^
  -application org.eclipse.equinox.p2.artifact.repository.mirrorApplication ^
  -source https://download.eclipse.org/egit/updates ^
  -destination %DEST%\egit ^
  -verbose >> %LOG% 2>&1

%ECLIPSE% -nosplash ^
  -application org.eclipse.equinox.p2.metadata.repository.mirrorApplication ^
  -source https://download.eclipse.org/egit/updates ^
  -destination %DEST%\egit ^
  -verbose >> %LOG% 2>&1

echo [2/7] EGit 완료: %time% >> %LOG%
echo [2/7] 완료

:: -----------------------------------------------
:: 3. Buildship (Gradle)
:: -----------------------------------------------
echo.
echo [3/7] Buildship(Gradle) 미러링 시작...
echo [3/7] Buildship 시작: %time% >> %LOG%

%ECLIPSE% -nosplash ^
  -application org.eclipse.equinox.p2.artifact.repository.mirrorApplication ^
  -source https://download.eclipse.org/buildship/updates/e426/releases/3.x ^
  -destination %DEST%\buildship ^
  -verbose >> %LOG% 2>&1

%ECLIPSE% -nosplash ^
  -application org.eclipse.equinox.p2.metadata.repository.mirrorApplication ^
  -source https://download.eclipse.org/buildship/updates/e426/releases/3.x ^
  -destination %DEST%\buildship ^
  -verbose >> %LOG% 2>&1

echo [3/7] Buildship 완료: %time% >> %LOG%
echo [3/7] 완료

:: -----------------------------------------------
:: 4. Mylyn
:: -----------------------------------------------
echo.
echo [4/7] Mylyn 미러링 시작...
echo [4/7] Mylyn 시작: %time% >> %LOG%

%ECLIPSE% -nosplash ^
  -application org.eclipse.equinox.p2.artifact.repository.mirrorApplication ^
  -source https://download.eclipse.org/mylyn/releases/latest ^
  -destination %DEST%\mylyn ^
  -verbose >> %LOG% 2>&1

%ECLIPSE% -nosplash ^
  -application org.eclipse.equinox.p2.metadata.repository.mirrorApplication ^
  -source https://download.eclipse.org/mylyn/releases/latest ^
  -destination %DEST%\mylyn ^
  -verbose >> %LOG% 2>&1

echo [4/7] Mylyn 완료: %time% >> %LOG%
echo [4/7] 완료

:: -----------------------------------------------
:: 5. DTP (DataTools)
:: -----------------------------------------------
echo.
echo [5/7] DTP(DataTools) 미러링 시작...
echo [5/7] DTP 시작: %time% >> %LOG%

%ECLIPSE% -nosplash ^
  -application org.eclipse.equinox.p2.artifact.repository.mirrorApplication ^
  -source https://download.eclipse.org/datatools/updates/1.16 ^
  -destination %DEST%\datatools ^
  -verbose >> %LOG% 2>&1

%ECLIPSE% -nosplash ^
  -application org.eclipse.equinox.p2.metadata.repository.mirrorApplication ^
  -source https://download.eclipse.org/datatools/updates/1.16 ^
  -destination %DEST%\datatools ^
  -verbose >> %LOG% 2>&1

echo [5/7] DTP 완료: %time% >> %LOG%
echo [5/7] 완료

:: -----------------------------------------------
:: 6. Subversive (SVN)
:: -----------------------------------------------
echo.
echo [6/7] Subversive(SVN) 미러링 시작...
echo [6/7] SVN 시작: %time% >> %LOG%

%ECLIPSE% -nosplash ^
  -application org.eclipse.equinox.p2.artifact.repository.mirrorApplication ^
  -source https://download.eclipse.org/technology/subversive/4.8/update-site ^
  -destination %DEST%\svn ^
  -verbose >> %LOG% 2>&1

%ECLIPSE% -nosplash ^
  -application org.eclipse.equinox.p2.metadata.repository.mirrorApplication ^
  -source https://download.eclipse.org/technology/subversive/4.8/update-site ^
  -destination %DEST%\svn ^
  -verbose >> %LOG% 2>&1

echo [6/7] SVN 완료: %time% >> %LOG%
echo [6/7] 완료

:: -----------------------------------------------
:: 7. BytecodeOutline
:: -----------------------------------------------
echo.
echo [7/7] BytecodeOutline 미러링 시작...
echo [7/7] BytecodeOutline 시작: %time% >> %LOG%

%ECLIPSE% -nosplash ^
  -application org.eclipse.equinox.p2.artifact.repository.mirrorApplication ^
  -source https://andrei.gmxhome.de/eclipse/ ^
  -destination %DEST%\bytecodeoutline ^
  -verbose >> %LOG% 2>&1

%ECLIPSE% -nosplash ^
  -application org.eclipse.equinox.p2.metadata.repository.mirrorApplication ^
  -source https://andrei.gmxhome.de/eclipse/ ^
  -destination %DEST%\bytecodeoutline ^
  -verbose >> %LOG% 2>&1

echo [7/7] BytecodeOutline 완료: %time% >> %LOG%
echo [7/7] 완료

:: -----------------------------------------------
:: 서드파티 jar 다운로드 (curl 사용)
:: -----------------------------------------------
echo.
echo [서드파티] jar 다운로드 시작...
echo [서드파티] 시작: %time% >> %LOG%

curl -L -o %DEST%\thirdparty\commons-dbcp2-2.1.1.jar ^
  https://repo1.maven.org/maven2/org/apache/commons/commons-dbcp2/2.1.1/commons-dbcp2-2.1.1.jar

curl -L -o %DEST%\thirdparty\commons-pool2-2.4.2.jar ^
  https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.4.2/commons-pool2-2.4.2.jar

curl -L -o %DEST%\thirdparty\jackson-core-2.5.0.jar ^
  https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-core/2.5.0/jackson-core-2.5.0.jar

curl -L -o %DEST%\thirdparty\jackson-databind-2.5.4.jar ^
  https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-databind/2.5.4/jackson-databind-2.5.4.jar

curl -L -o %DEST%\thirdparty\jackson-annotations-2.5.0.jar ^
  https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-annotations/2.5.0/jackson-annotations-2.5.0.jar

curl -L -o %DEST%\thirdparty\velocity-1.7.jar ^
  https://repo1.maven.org/maven2/org/apache/velocity/velocity/1.7/velocity-1.7.jar

curl -L -o %DEST%\thirdparty\derby-10.10.2.0.jar ^
  https://repo1.maven.org/maven2/org/apache/derby/derby/10.10.2.0/derby-10.10.2.0.jar

echo [서드파티] 완료: %time% >> %LOG%
echo [서드파티] 완료

:: -----------------------------------------------
:: 완료
:: -----------------------------------------------
echo.
echo ================================================
echo  전체 미러링 완료!
echo  로그파일: %LOG%
echo  결과폴더: %DEST%
echo ================================================
echo 종료시간: %date% %time% >> %LOG%

pause
