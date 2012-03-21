%Module italc 0

%Import QtCore/QtCoremod.sip
%Import QtGui/QtGuimod.sip

class AuthenticationCredentials {

%TypeHeaderCode
#include <libitalc/AuthenticationCredentials.h>
%End

public:
	enum TypeFlags
	{
		PrivateKey = 0x01,
		UserLogon = 0x02,
		CommonSecret = 0x04
	} ;

	void setLogonUsername( const QString &username );
    void setLogonPassword( const QString &password );

} ;


class ItalcConfiguration
{

%TypeHeaderCode
#include <libitalc/ItalcConfiguration.h>
%End

public:
	ItalcConfiguration();

	void setLogLevel( int );
	void setLogToStdErr( bool );
	void setLimittedLogFileSize( bool );
	void setLogFileSizeLimit( int );
	void setLogFileDirectory( const QString & );
	void setKeyAuthenticationEnabled( bool );
	void setLogonAuthenticationEnabled( bool );
	void setPrivateKeyBaseDir( const QString & );
	void setPublicKeyBaseDir( const QString & );
	void setLogonGroups( const QStringList & );

} ;


namespace ItalcCore {

%TypeHeaderCode
#include <libitalc/ItalcCore.h>
%End

	bool init();
	bool initAuthentication( int credentialTypes );
	void destroy();

	ItalcConfiguration *config;
	AuthenticationCredentials *authenticationCredentials;

	enum UserRoles
	{
		RoleNone,
		RoleTeacher,
		RoleAdmin,
		RoleSupporter,
		RoleOther,
		RoleCount
	} ;
	typedef ItalcCore::UserRoles UserRole;

	void setRole( ItalcCore::UserRole role );
%MethodCode
		ItalcCore::role = a0;
%End

} ;


class ItalcCoreConnection : QObject {

%TypeHeaderCode
#include <libitalc/ItalcCoreConnection.h>
%End

public:
	ItalcCoreConnection( ItalcVncConnection *vncConn );
	~ItalcCoreConnection();

	ItalcVncConnection *vncConnection();
	bool isConnected() const;

	const QString &user() const;
	const QString &userHomeDir();

	int slaveStateFlags() const;

	bool isDemoServerRunning() const;
	bool isDemoClientRunning() const;
	bool isScreenLockRunning() const;
	bool isInputLockRunning() const;
	bool isSystemTrayIconRunning() const;
	bool isMessageBoxRunning() const;

	void sendGetUserInformationRequest();
	void execCmds( const QString &cmds);
	void startDemo( const QString &host, int port, bool fullscreen = false );
	void stopDemo();
	void lockScreen();
	void unlockScreen();
	void lockInput();
	void unlockInput();
	void logonUser( const QString &uname, const QString &pw, const QString &domain );
	void logoutUser();
	void displayTextMessage( const QString &msg );

	void powerOnComputer( const QString &mac );
	void powerDownComputer();
	void restartComputer();
	void disableLocalInputs( bool disabled );

	void setRole( const ItalcCore::UserRole role );

	void startDemoServer( int sourcePort, int destinationPort );
	void stopDemoServer();
	void demoServerAllowHost( const QString &host );
	void demoServerUnallowHost( const QString &host );

	void reportSlaveStateFlags();

signals:
	void receivedUserInfo( const QString &, const QString & );
	void receivedSlaveStateFlags( const int );

private:
	ItalcCoreConnection( const ItalcCoreConnection& );

};


class ItalcVncConnection : QObject {

%TypeHeaderCode
#include <libitalc/ItalcVncConnection.h>
%End

public:
	enum QualityLevels
	{
		ThumbnailQuality,
		SnapshotQuality,
		RemoteControlQuality,
		DemoServerQuality,
		DemoClientQuality,
		NumQualityLevels
	} ;

	enum States
	{
		Disconnected,
		HostUnreachable,
		AuthenticationFailed,
		ConnectionFailed,
		Connected
	} ;

	ItalcVncConnection( QObject *parent = NULL );
	virtual ~ItalcVncConnection();

	const QImage image( int x = 0, int y = 0, int w = 0, int h = 0 );
	QImage scaledScreen();

	void start();
	void stop();

	void reset( const QString &host );
	void setHost( const QString &host );
	void setPort( int port );

	States state() const;
	bool isConnected() const;
	bool isRunning() const;

	void setQuality( QualityLevels q );
	QualityLevels quality() const;

	QSize framebufferSize() const;
	void setScaledSize( const QSize &s );
	void rescaleScreen();

	void setFramebufferUpdateInterval( int interval );

signals:
	void stateChanged( const States );

private:
	ItalcVncConnection( const ItalcVncConnection& );

};



class Logger {

%TypeHeaderCode
#include <libitalc/Logger.h>
%End

public:
	enum LogLevels
	{
		LogLevelNothing,
		LogLevelCritical,
		LogLevelError,
		LogLevelWarning,
		LogLevelInfo,
		LogLevelDebug,
		NumLogLevels
	} ;

	Logger( const QString &appName );
	~Logger();

} ;

