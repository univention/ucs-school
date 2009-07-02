%Module italc 0

%Import QtCore/QtCoremod.sip
%Import QtGui/QtGuimod.sip

struct ISD {
%TypeHeaderCode
#include <libitalc/isd_base.h>
%End

public:
	enum userRoles
	{
		RoleNone,
		RoleTeacher,
		RoleAdmin,
		RoleSupporter,
		RoleOther,
		RoleCount
	} ;

};

//void __setRole( ISD::userRoles );

class isdConnection {

%TypeHeaderCode
#include <libitalc/isd_connection.h>
%End

public:
	enum states
	{
		Disconnected,
		Connecting,
		Connected,
		HostUnreachable,
		ConnectionRefused,
		ConnectionFailed,
		InvalidServer,
		AuthFailed,
		UnknownError
	};
	isdConnection( const QString & _host, QObject * _parent = 0 );
	virtual ~isdConnection();
	virtual states open( );
	virtual void close( );
	void gracefulClose( );
	states reset( const QString & _host = "", int * _cnt = NULL );
	states state( ) const;
	bool hasData( ) const;
	bool handleServerMessages( );
	//bool handleServerMessages( bool _send_screen_update );

	const QString & user( );
	const QString & userHomeDir( );
	QString host( ) const;
	int port( ) const;
	int demoServerPort( ) const;

	bool sendGetUserInformationRequest( );
	bool execCmds( const QString & _cmd );
	bool startDemo( const QString & _port, bool _full_screen = FALSE );
	bool stopDemo( );
	bool lockDisplay( );
	bool unlockDisplay( );
	bool logonUser( const QString & _uname, const QString & _pw,
						const QString & _domain );
	bool logoutUser( );
	bool displayTextMessage( const QString & _msg );
	bool sendFile( const QString & _fname );
	bool collectFiles( const QString & _nfilter );

	bool wakeOtherComputer( const QString & _mac );
	bool powerDownComputer( );
	bool restartComputer( );
	bool disableLocalInputs( bool _disabled );

	bool setRole( const ISD::userRoles _role );
	bool demoServerRun( int _quality, int _port );
	bool demoServerAllowClient( const QString & _client );
	bool demoServerDenyClient( const QString & _client );

	bool hideTrayIcon( );
	//static bool initAuthentication( );
	static bool initAuthentication( const ISD::userRoles &role=ISD::RoleOther );
%MethodCode
	__role=a0;
	bool res=isdConnection::initAuthentication();
    sipRes=Py_BuildValue("b",res);
%End
private:
	isdConnection(const isdConnection&);
};

class ivsConnection : isdConnection {

%TypeHeaderCode
#include <libitalc/ivs_connection.h>
%End

public:
	enum quality
	{
		QualityLow,
		QualityMedium,
		QualityHigh,
		QualityDemoLow,
		QualityDemoMedium,
		QualityDemoHigh
	};

	ivsConnection( const QString & _host, quality _q = QualityLow,
						bool _use_auth_file = FALSE,
						QObject * _parent = NULL );

	virtual ~ivsConnection();
	virtual void close(  );
	QImage scaledScreen(  );
	const QImage & screen(  ) const;
	QSize framebufferSize(  ) const;
	void setScaledSize( const QSize & _s );
	void rescaleScreen(  );
	bool handleServerMessages( bool _send_screen_update, int _tries = 5 );
	bool softwareCursor(  ) const;
	const QPoint & cursorPos(  ) const;
	const QPoint & cursorHotSpot(  ) const;
	QImage cursorShape(  ) const;
	bool takeSnapshot(  );

private:
	ivsConnection(const ivsConnection&);
};
