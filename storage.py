import pickle


class Storage:
	def __init__(self):
		self._users = []
		self._groups = []
		self._report = Report()
		self.load_users()
		self.load_groups()
		self.load_report()

	def save_users(self, users):
		try:
			self._users = users;
			pickle.dump(self._users, open('users.p', 'wb'))
			return self._users
		except (ValueError, Exception):
			return []

	def load_users(self):
		try:
			self._users = pickle.load(open('users.p', 'rb'))
			return self._users
		except FileNotFoundError:
			return self.save_users()
		except (ValueError, Exception):
			return []

	def save_groups(self, groups):
		try:
			self._groups = groups
			pickle.dump(self._groups, open('groups.p', 'wb'))
			return self._groups
		except (ValueError, Exception):
			return []

	def load_groups(self):
		try:
			self._groups = pickle.load(open('groups.p', 'rb'))
			return self._groups
		except FileNotFoundError:
			return self.save_groups()
		except (ValueError, Exception):
			return []

	def save_report(self, report):
		try:
			self._report = report
			pickle.dump(self._report, open('report.p', 'wb'))
			return self._report
		except (ValueError, Exception):
			return Report()

	def load_report(self):
		try:
			self._report = pickle.load(open('report.p', 'rb'))
			return self._report
		except FileNotFoundError:
			return self.save_report()
		except (ValueError, Exception):
			return Report()


class Report:
	def __init__(self):
		self.n_completed_groups = 0


storage = Storage()
