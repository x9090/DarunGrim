import sqlalchemy
from sqlalchemy import Table, Column, Integer, String, Binary, MetaData, ForeignKey
from sqlalchemy.orm import mapper, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy import and_

Base = declarative_base()

class Patch(Base):
	__tablename__ = 'patches'
	
	id = Column( Integer, primary_key = True )
	name = Column( String )
	title = Column( String )
	url = Column( String )
	html_data = Column( Binary ) 

	def __init__( self, name, title, url, html_data ):
		self.name = name
		self.title = title
		self.url = url
		self.html_data = html_data
		
	def __repr__( self ):
		return "<Patches('%s','%s','%s')>" % ( self.name, self.title, self.url )

class CVE(Base):
	__tablename__ = 'cves'
	id = Column( Integer, primary_key = True )
	cve_string = Column( String )	
	name = Column( String )	

	patch_id = Column( Integer, ForeignKey('patches.id'))
	patches = relationship(Patch, backref=backref('cves', order_by=id))

	def __init__( self, cve_string, name ):
		self.cve_string = cve_string
		self.name = name
		
	def __repr__( self ):
		return "<CVEs('%s','%s')>" % ( self.cve_string, self.name )

class Download(Base):
	__tablename__ = 'downloads'
	id = Column( Integer, primary_key = True )
	operating_system = Column( String )
	label = Column( String )	
	url = Column( String )
	filename = Column( String )
	maximum_security_impact = Column( String )
	aggregate_severity_rating = Column( String )
	bulletins_replaced = Column( String )

	patch_id = Column( Integer, ForeignKey('patches.id'))
	patches = relationship(Patch, backref=backref('downloads', order_by=id))

	def __init__( self, operating_system, label, url, filename, maximum_security_impact, aggregate_severity_rating, bulletins_replaced ):
		self.operating_system = operating_system
		self.label = label
		self.url = url
		self.filename = filename
		self.maximum_security_impact = maximum_security_impact
		self.aggregate_severity_rating = aggregate_severity_rating
		self.bulletins_replaced = bulletins_replaced
		
	def __repr__( self ):
		return "<Downloads('%s','%s','%s')>" % ( self.label, self.url, self.filename )
 
class FileIndex(Base):
	__tablename__ = 'fileindexes'
	
	id = Column( Integer, primary_key = True )
	operating_system = Column( String )
	service_pack = Column( String )
	filename = Column( String )
	company_name = Column( String )
	version_string = Column( String )
	patch_identifier = Column( String ) #ex) MS09-011
	version_number = Column( String )
	release_plan = Column( String )
	full_path = Column( String )

	download_id = Column( Integer, ForeignKey('downloads.id'))
	downloads = relationship(Download, backref=backref('fileindexes', order_by=id))

	def __init__( self, operating_system, service_pack, filename, company_name, version_string, patch_identifier, full_path ):
		self.operating_system = operating_system
		self.service_pack = service_pack
		self.filename = filename
		self.company_name = company_name
		self.version_string = version_string
		self.patch_identifier = patch_identifier
		#Parser version_string
		version_string_parted = version_string.split(" (")
		if len( version_string_parted ) == 2:
			( self.version_number, description ) = version_string_parted
			for part in description.split('.'):
				for part2 in part.split('_'):
					if part2 == 'qfe' or part2 == 'gdr':
						self.release_plan = part2

					elif part2 in [ 'xpsp', 'vista', 'srv03' ]:
						self.operating_system = part2

					elif part2[0:2] == 'sp':
						self.service_pack = part2

		self.full_path = full_path

	def GetVersionDetailList( self ):
		(os_string, sp_string, os_type, os_code, build_number) = self.ParseVersionString( self.version_string )
		return (self.id, self.full_path,os_string, sp_string, os_type, os_code, build_number)

	def GetVersionDetail( self ):
		(id, full_path, os_string, sp_string, os_type, os_code, build_number) = self.GetVersionDetailList()
		file_entry = {}
		file_entry['id'] = id
		file_entry['full_path'] = full_path
		file_entry['os_code'] = os_code
		file_entry['os_string'] = os_string
		file_entry['sp_string'] = sp_string
		file_entry['os_type'] = os_type
		file_entry['build_number'] = build_number
		return file_entry

	def ParseVersionString( self, version_string ):
		main_parts = version_string.split( ' ' )

		identifier = ''
		version = ''
		if len( main_parts ) == 1:
			version = main_parts[0]
		elif len( main_parts ) == 2:
			( version, identifier ) = main_parts

		#### Version
		version_parts = version.split('.')
		
		os_code = ''
		build_number = ''
		if len( version_parts ) > 3:
			os_code = version_parts[0]+'.'+version_parts[1]+'.'+version_parts[2]
			build_number = version_parts[3]

		
		#### Distro
		dot_pos = identifier.find(".")
		distro=''
		if dot_pos >= 0:
			distro = identifier[:dot_pos]
		distro = distro[1:]
		distro_parts = distro.split( '_' )
		os_string = ''
		sp_string = ''
		os_type = ''
		if len( distro_parts ) == 2:
			os_string = distro_parts[0]
			if os_string == 'xpsp2':
				os_string = 'xpsp'
				sp_string = 'sp2'
			elif os_string == 'xpclnt':
				os_string = 'xpsp'

		elif len( distro_parts ) == 3:
			os_string = distro_parts[0]
			sp_string = distro_parts[1]
			os_type = distro_parts[2]

		return (os_string, sp_string, os_type, os_code, build_number)

	def __repr__( self ):
		return "<FileIndex('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s' )>" % ( self.operating_system, self.service_pack, self.filename, self.company_name, self.version_string, self.patch_identifier, self.version_number, self.release_plan, self.full_path )

class Database:
	DebugLevel = 2
	def __init__( self, filename ):
		echo = False
		if self.DebugLevel > 2:
			echo = True
		self.Engine = sqlalchemy.create_engine( 'sqlite:///' + filename, echo = echo )

		metadata = Base.metadata
		metadata.create_all( self.Engine )

		self.Session = sessionmaker()
		self.Session.configure( bind = self.Engine )	
		self.SessionInstance = self.Session()

	def AddPatch( self, name, title, url, html_data = '' ):
		patch = Patch( name, title, url, html_data )
		self.SessionInstance.add ( patch )
		return patch

	def GetPatch( self, name ):
		return self.SessionInstance.query( Patch ).filter_by( name=name ).first() 

	def GetPatches( self ):
		return self.SessionInstance.query( Patch ).order_by( Patch.name ).all()

	def GetPatchByID( self, id ):
		return self.SessionInstance.query( Patch ).filter_by( id = id ).all()

	def GetPatchNameByID( self, id ):
		for patch in self.SessionInstance.query( Patch ).filter_by( id = id ).all():
			return patch.name
		return ''

	def AddCVE( self, patch, cve_string, name ):
		cve = CVE( cve_string, name )
		if patch:
			patch.cves.append( cve )
		else:
			self.SessionInstance.add( cve )
		return cve

	def AddDownload( self, patch, operating_system, name, url, filename, maximum_security_impact, aggregate_severity_rating, bulletins_replaced ):
		download = Download( operating_system, name, url, filename, maximum_security_impact, aggregate_severity_rating, bulletins_replaced )
		if patch:
			patch.downloads.append( download )
		else:
			self.SessionInstance.add( download )
		return download

	def GetDownloadByFilename( self , filename ):
		return self.SessionInstance.query( Download ).filter_by( filename=filename ).first() 
	
	def GetDownloadByPatchID( self , patch_id ):
		return self.SessionInstance.query( Download ).filter_by( patch_id=patch_id ).all()

	def GetDownloads( self ):
		return self.SessionInstance.query( Download ).filter(~Download.id.in_(self.SessionInstance.query(FileIndex.download_id)))

	def GetDownloadID( self, id ):
		return self.SessionInstance.query( Download ).filter_by( id=id ).all() 

	def GetDownloadByID( self, id ):
		return self.SessionInstance.query( Download ).filter_by( id=id ).all() 

	def GetDownloadLabelByID( self, id ):
		for download in self.GetDownloadID( id ):
			return download.label
		return ''

	def GetFileByID( self, id ):
		return self.SessionInstance.query( FileIndex ).filter_by( id=id ).all()

	def GetFileNameByID( self, id ):
		for file_index in self.SessionInstance.query( FileIndex ).filter_by( id=id ).all():
			return file_index.filename
		return ''

	def GetFileByFileName( self, filename ):
		return self.SessionInstance.query( FileIndex ).filter( FileIndex.filename==filename ).all()

	def GetFiles( self ):
		return self.SessionInstance.query( FileIndex ).all()

	def GetFileNames( self, company_name = None ):
		if company_name != None:
			return self.SessionInstance.query( FileIndex.filename ).filter( FileIndex.company_name==company_name ).distinct().all()
		return self.SessionInstance.query( FileIndex.filename ).distinct().all()

	def GetCompanyNames( self ):
		return self.SessionInstance.query( FileIndex.company_name ).distinct().all()

	def GetVersionStrings( self, company_name = None, filename = None ):
		if company_name !=None and filename != None:
			return self.SessionInstance.query( FileIndex.version_string ).filter( and_(FileIndex.company_name==company_name, FileIndex.filename==filename) ).distinct().all()
			
		return self.SessionInstance.query( FileIndex.version_string ).distinct().all()

	def GetVersionStringsWithIDs( self, company_name = None, filename = None ):
		if company_name !=None and filename != None:
			return self.SessionInstance.query( FileIndex.id, FileIndex.version_string ).filter( and_(FileIndex.company_name==company_name, FileIndex.filename==filename) ).distinct().order_by( FileIndex.version_string ).all()
			
		return self.SessionInstance.query( FileIndex.id, FileIndex.version_string ).distinct().all()

	def GetFileByFileInfo( self, filename, company_name, version_string ):
		return self.SessionInstance.query( FileIndex ).filter( and_( FileIndex.filename==filename, FileIndex.company_name==company_name, FileIndex.version_string==version_string ) ).all()

	def GetFileByDownloadID( self, download_id ):
		return self.SessionInstance.query( FileIndex ).filter_by( download_id=download_id ).all()

	def AddFile(self, download, operating_system, service_pack, filename, company_name, version_string, patch_identifier, full_path ):
		fileindex = FileIndex( operating_system, service_pack, filename, company_name, version_string, patch_identifier, full_path )
		if download:
			download.fileindexes.append( fileindex )
		else:
			self.SessionInstance.add( fileindex )
		return fileindex

	def UpdateFile(self, download, operating_system, service_pack, filename, company_name, version_string, patch_identifier, full_path ):
		for file in self.SessionInstance.query( FileIndex ).filter( and_( FileIndex.filename==filename, FileIndex.company_name==company_name, FileIndex.version_string==version_string ) ).all():
			file.operating_system = operating_system
			file.service_pack = service_pack
			file.filename = filename
			file.company_name = company_name
			file.version_string = version_string 
			file.patch_identifier = patch_identifier
			file.full_path = full_path

		if download:
			download.fileindexes.append( fileindex )
		else:
			self.SessionInstance.add( fileindex )
		return fileindex

	def Commit( self ):
		try:
			self.SessionInstance.commit()
			return True
		except:
			print 'Failed to Commit'
			import traceback
			traceback.print_exc()
			self.SessionInstance.rollback()
			return False

if __name__ == '__main__':
	Tests = [ "RenameFiles" ]

	#database_name = 'adobe.db'
	database_name = r'..\UI\Web\index.db'

	database = Database( database_name )
	if "DumpFiles" in Tests:
		company_names = database.GetCompanyNames()
		filenames = database.GetFileNames()
		version_strings = database.GetVersionStrings()
	
		for (company_name,) in company_names:
			print company_name
			for (filename, ) in database.GetFileNames( company_name ):
				print '\t', filename
				for (version_string, ) in database.GetVersionStrings( company_name, filename ):
					print '\t\t',version_string
	if "AddPatch" in Tests:
		operating_system = "os"
		service_pack = "sp"
		filename = "fn"
		company_name = "company"
		version_string = "version"
		patch_identifier = "patch"
		full_path = "full"	

		maximum_security_impact = 'Remote Code Execution'
		aggregate_severity_rating = 'Critical'
		bulletins_replaced = 'MS08-011'

		patch = database.AddPatch( 'MS09-011', 'Vulnerability in Microsoft DirectShow Could Allow Remote Code Execution (961373)', 'http://www.microsoft.com/technet/security/bulletin/ms09-011.mspx' )
		download = database.AddDownload( patch, 'Microsoft Windows 2000 Service Pack 4', 'DirectX 8.1', 'http://download.microsoft.com/download/5/1/A/51A85157-C145-4C4C-8F15-546A564EA841/Windows2000-DirectX8-KB961373-x86-ENU.exe', 'Patches/Windows2000-DirectX8-KB961373-x86-ENU.exe', maximum_security_impact, aggregate_severity_rating, bulletins_replaced )
		database.AddFile( download, operating_system, service_pack, filename, company_name, version_string, patch_identifier, full_path )
		
		download = database.AddDownload( patch, 'Microsoft Windows 2000 Service Pack 4','DirectX 8.1', 'http://download.microsoft.com/download/5/1/A/51A85157-C145-4C4C-8F15-546A564EA841/Windows2000-DirectX8-KB961373-x86-ENU.exe', 'Patches/Windows2000-DirectX8-KB961373-x86-ENU.exe', maximum_security_impact, aggregate_severity_rating, bulletins_replaced )
		database.AddFile( download, operating_system, service_pack, filename, company_name, version_string, patch_identifier, full_path )

		database.AddDownload( patch, 'Microsoft Windows 2000 Service Pack 4', 'DirectX 8.1', 'http://download.microsoft.com/download/5/1/A/51A85157-C145-4C4C-8F15-546A564EA841/Windows2000-DirectX8-KB961373-x86-ENU.exe', 'Patches/Windows2000-DirectX8-KB961373-x86-ENU.exe', maximum_security_impact, aggregate_severity_rating, bulletins_replaced )
		database.AddDownload( patch, 'Microsoft Windows 2000 Service Pack 4', 'DirectX 8.1', 'http://download.microsoft.com/download/5/1/A/51A85157-C145-4C4C-8F15-546A564EA841/Windows2000-DirectX8-KB961373-x86-ENU.exe', 'Patches/Windows2000-DirectX8-KB961373-x86-ENU.exe', maximum_security_impact, aggregate_severity_rating, bulletins_replaced )
		database.Commit()

	if "GetPatch" in Tests:
		print 'MS09-018',database.GetPatch( 'MS09-018' )
		print 'MS09-0999',database.GetPatch( 'MS09-099' )
		
	if "RenameFiles" in Tests:
		for file in database.GetFiles():
			try:
				#file.full_path = file.full_path.replace( "T:\\mat\\Projects\\", "" )
				file.full_path = file.full_path.replace( "Binaries\\", "" )
			except:
				pass
		database.Commit()

