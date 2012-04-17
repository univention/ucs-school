Folgende Liste umfasst alle benutzten UCR-Variablen:
  proxy/filter/{setting,usergroup,groupdefault,room,setting-user}

==== Filterregeln ====

proxy/filter/setting/<ruleName>/{filtertype,url,domain,priority,wlan}

proxy/filter/setting/<ruleName>/filtertype={whitelist-block,blacklist-pass,whitelist-blacklist-pass}
  -> setzt den Typ für die Filterregel:
  whitelist-block
    Ist Domain/URL auf whitelist?
      Zugriff wird erlaubt
    wenn nicht
      Zugriff wird verweigert
  blacklist-pass
    Ist Domain/URL auf blacklist?
      Zugriff wird verweigert
    wenn nicht
      Zugriff wird erlaubt
  whitelist-blacklist-pass (obsolete)
    Ist Domain/URL auf whitelist?
      Zugriff wird erlaubt
    wenn nicht
      ist Domain/URL auf blacklist?
  	  Zugriff wird verweigert
      wenn nicht
  	  Zugriff wird erlaubt

proxy/filter/setting/<ruleName>/{url,domain}/{blacklisted,whitelisted}/{1..99}
  -> definiert die Einträge der black-/whitelists von URLs/Domains

proxy/filter/setting/<ruleName>/priority={0..infinity}
  -> Integer, größer ist wichtiger als niedriger, nach oben hin gibt es keine Beschränkung

proxy/filter/setting/<ruleName>/wlan={true,false}
  -> Definiert, ob der WLAN-Zugriff erlaubt ist, Defaultwert ist "false"


proxy/filter/groupdefault/<groupName>=<ruleName>
  -> Regel <ruleName> (proxy/filter/setting) ist für Gruppe <groupName> gesetzt


Beispiele:
  proxy/filter/setting/bla/priority: 90
  proxy/filter/setting/bla/wlan: false
  proxy/filter/setting/blubb/priority: 100
  proxy/filter/setting/blubb/wlan: true
  proxy/filter/groupdefault/musterschule-1A: Kein_Internet
  proxy/filter/groupdefault/musterschule-2B: Kein_Internet
  proxy/filter/setting/Kein_Internet/filtertype: whitelist-block
  proxy/filter/setting/Wikipedia/domain/whitelisted/1: wikipedia.org
  proxy/filter/setting/Wikipedia/domain/whitelisted/2: wikipedia.de
  proxy/filter/setting/Wikipedia/filtertype: whitelist-block
  proxy/filter/setting/black-white/filtertype: whitelist-blacklist-pass


==== Raumbezogene Filtereinstellungen ====

proxy/filter/setting-user
  -> wie proxy/filter/setting, definiert temporäre Regel für einen Benutzer (darüber kann bspw. ein Lehrer seine eigenen Regeln bestimmen)

proxy/filter/room/<roomName>/ip
  -> definiert alle IPs, die zu dem Raum <roomName> gehören

proxy/filter/room/<roomName>/rule=<ruleName>
  -> setzt die Regel <ruleName> (temporäre Regeln aus proxy/filter/setting-user) für den Raum <roomName>


==== Sonstige Variablen ====

proxy/filter/usergroup/<groupName>
  -> <groupName> ist der Name der entsprechenden LDAP-Gruppe mit allen enthaltenen Benutzern,
     wird zu Caching-Zwecken auf UCR-Ebene verwendet

Beispiele:
  proxy/filter/usergroup/musterschule-1A: anton1,anton11,bertram9,christina7,daniela5,ernst3,friderike1,friderike11,gisela9,hans7,ines5,jens3,klaus1,klaus11,lisa9,marlene7,norbert5,otto3,pauline1,pauline11,richard9,silke7,tim5,ulrike3,victor1,victor11,wilhelmine9,d.krause1,d.lehmann1,g.krause1,g.lehmann1
  proxy/filter/usergroup/musterschule-1B: anton2,anton12,bertram10,christina8,daniela6,ernst4,friderike2,friderike12,gisela10,hans8,ines6,jens4,klaus2,klaus12,lisa10,marlene8,norbert6,otto4,pauline2,pauline12,richard10,silke8,tim6,ulrike4,victor2,victor12,wilhelmine10,d.krause1,d.lehmann1,g.krause1,g.lehmann1
  proxy/filter/usergroup/musterschule-2A: anton3,bertram1,bertram11,christina9,daniela7,ernst5,friderike3,gisela1,gisela11,hans9,ines7,jens5,klaus3,lisa1,lisa11,marlene9,norbert7,otto5,pauline3,richard1,richard11,silke9,tim7,ulrike5,victor3,wilhelmine1,wilhelmine11,d.krause1,d.lehmann1,g.krause1,g.lehmann1
  proxy/filter/usergroup/musterschule-2B: anton4,bertram2,bertram12,christina10,daniela8,ernst6,friderike4,gisela2,gisela12,hans10,ines8,jens6,klaus4,lisa2,lisa12,marlene10,norbert8,otto6,pauline4,richard2,richard12,silke10,tim8,ulrike6,victor4,wilhelmine2,wilhelmine12,d.krause1,d.lehmann1,g.krause1,g.lehmann1
  proxy/filter/usergroup/musterschule-3B: anton5,bertram3,christina1,christina11,daniela9,ernst7,friderike5,gisela3,hans1,hans11,ines9,jens7,klaus5,lisa3,marlene1,marlene11,norbert9,otto7,pauline5,richard3,silke1,silke11,tim9,ulrike7,victor5,wilhelmine3,d.krause1,d.lehmann1,g.krause1,g.lehmann1
  proxy/filter/usergroup/musterschule-3C: anton6,bertram4,christina2,christina12,daniela10,ernst8,friderike6,gisela4,hans2,hans12,ines10,jens8,klaus6,lisa4,marlene2,marlene12,norbert10,otto8,pauline6,richard4,silke2,silke12,tim10,ulrike8,victor6,wilhelmine4,d.krause1,d.lehmann1,g.krause1,g.lehmann1
  proxy/filter/usergroup/musterschule-4B: anton7,bertram5,christina3,daniela1,daniela11,ernst9,friderike7,gisela5,hans3,ines1,ines11,jens9,klaus7,lisa5,marlene3,norbert1,norbert11,otto9,pauline7,richard5,silke3,tim1,tim11,ulrike9,victor7,wilhelmine5,d.krause1,d.lehmann1,g.krause1,g.lehmann1
  proxy/filter/usergroup/musterschule-4r: anton8,bertram6,christina4,daniela2,daniela12,ernst10,friderike8,gisela6,hans4,ines2,ines12,jens10,klaus8,lisa6,marlene4,norbert2,norbert12,otto10,pauline8,richard6,silke4,tim2,tim12,ulrike10,victor8,wilhelmine6,d.krause1,d.lehmann1,g.krause1,g.lehmann1
  proxy/filter/usergroup/musterschule-Froesche: anton9,bertram7,christina5,daniela3,ernst1,ernst11,friderike9,gisela7,hans5,ines3,jens1,jens11,klaus9,lisa7,marlene5,norbert3,otto1,otto11,pauline9,richard7,silke5,tim3,ulrike1,ulrike11,victor9,wilhelmine7,d.krause1,d.lehmann1,g.krause1,g.lehmann1
  proxy/filter/usergroup/musterschule-Igel: anton10,bertram8,christina6,daniela4,ernst2,ernst12,friderike10,gisela8,hans6,ines4,jens2,jens12,klaus10,lisa8,marlene6,norbert4,otto2,otto12,pauline10,richard8,silke6,tim4,ulrike2,ulrike12,victor10,wilhelmine8,d.krause1,d.lehmann1,g.krause1,g.lehmann1
  proxy/filter/usergroup/musterschule-InformatikAG: anton1,anton11,bertram9
