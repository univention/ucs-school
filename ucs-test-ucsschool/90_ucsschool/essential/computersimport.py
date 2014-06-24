from essential.importcomputers import ComputerImport as ComputerImportLib
from essential.importcomputers import Windows, MacOS, IPManagedClient
from ucsschool.lib.models import IPComputer as IPComputerLib
from ucsschool.lib.models import MacComputer as MacComputerLib
from ucsschool.lib.models import WindowsComputer as WindowsComputerLib

class ComputerImport(ComputerImportLib):
	def __init__(self, school=None, nr_windows=0, nr_macos=0, nr_ipmanagedclient=0):

		self.school = school if school else uts.random_name()

		self.windows = []
		for i in range(0, nr_windows):
			self.windows.append(Windows(self.school))
		self.windows[1].set_inventorynumbers()
		self.windows[2].set_zone_verwaltng()

		self.memberservers = []

		self.macos = []
		for i in range(0, nr_macos):
			self.macos.append(MacOS(self.school))
		self.macos[0].set_inventorynumbers()
		self.macos[1].set_zone_edukativ()

		self.ipmanagedclients = []
		for i in range(0, nr_ipmanagedclient):
			self.ipmanagedclients.append(IPManagedClient(self.school))
		self.ipmanagedclients[0].set_inventorynumbers()
		self.ipmanagedclients[0].set_zone_edukativ()
		self.ipmanagedclients[1].set_zone_edukativ()

	def run_import(self, open_ldap_co):

		def _set_kwargs(computer):
			kwargs = {
					'school': computer.school,
					'name': computer.name,
					'ip_address': computer.ip,
					'mac_address': computer.mac,
					'type_name': computer.ctype,
					'inventory_number': computer.inventorynumbers,
					'zone': computer.zone,
			}
			return kwargs

		for computer in self.windows:
			kwargs = _set_kwargs(computer)
			WindowsComputerLib(**kwargs).create(open_ldap_co)
		for computer in self.macos:
			kwargs = _set_kwargs(computer)
			MacComputerLib(**kwargs).create(open_ldap_co)
		for computer in self.ipmanagedclients:
			kwargs = _set_kwargs(computer)
			IPComputerLib(**kwargs).create(open_ldap_co)

def create_computers(open_ldap_co, school=None, nr_windows=0, nr_macos=0, nr_ipmanagedclient=0):

	print '********** Generate school data'
	computer_import = ComputerImport(school, nr_windows=nr_windows, nr_macos=nr_macos, nr_ipmanagedclient=nr_ipmanagedclient)

	print computer_import

	print '********** Create computers'
	computer_import.run_import(open_ldap_co)

	created_computers = []
	for computer in computer_import.windows:
		created_computers.append(computer)
	for computer in computer_import.macos:
		created_computers.append(computer)
	for computer in computer_import.ipmanagedclients:
		created_computers.append(computer)

	return created_computers
