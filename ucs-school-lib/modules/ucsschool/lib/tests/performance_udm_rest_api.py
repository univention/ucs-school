import sys
import random
import time
try:
	from urlparse import unquote  # py2
except ImportError:
	from urllib.parse import unquote  # py3
from multiprocessing import Pool
from typing import Dict, List, Optional, Tuple
import requests

try:
	PARALLELISM = int(sys.argv[1])
except (ValueError, IndexError):
	print("Usage: {} <paralellism>")
	sys.exit(1)

SCHOOL_OU = "DEMOSCHOOL"
STR_NUMERIC = u"0123456789"
STR_ALPHA = u"abcdefghijklmnopqrstuvwxyz"
STR_ALPHANUM = STR_ALPHA + STR_NUMERIC

LDAP_BASE_DN = "dc=uni,dc=dtr"
BASE_URL = "http://10.200.3.66/univention/udm/"
AUTH = ("Administrator", "univention")


def random_string(length=10, alpha=True, numeric=True):  # type: (Optional[int], Optional[bool], Optional[bool]) -> str
	result = ''
	for _ in range(length):
		if alpha and numeric:
			result += random.choice(STR_ALPHANUM)
		elif alpha:
			result += random.choice(STR_ALPHA)
		elif numeric:
			result += random.choice(STR_NUMERIC)
	return str(result)


def random_name(length=10):  # type: (Optional[int]) -> str
	"""
	create random name (1 ALPHA, 8 ALPHANUM, 1 ALPHA)
	"""
	return random_string(length=1, alpha=True, numeric=False) + random_string(length=(length - 2), alpha=True, numeric=True) + random_string(length=1, alpha=True, numeric=False)


def create_objs_via_UDM_HTTP_API_sequential(datas):  # type: (List[Dict[str, str]]) -> List[str]
	headers = {"Accept": "application/json", "Content-Type": "application/json"}
	url = "{}/users/user/".format(BASE_URL)
	res = []
	for data in datas:
		resp = requests.post(url, headers=headers, json=data, auth=AUTH)
		if resp.status_code != 201:
			print("resp.status_code={!r}".format(resp.status_code))
			print("resp.text={!r}".format(resp.text))
			print("resp.json()={!r}".format(resp.json()))
			print("resp.headers={!r}".format(resp.headers))
			raise RuntimeError("User creation failed.")
		obj_url = resp.headers["Location"]
		dn = unquote(obj_url.rsplit("/", 1)[-1])
		res.append(dn)
	return res


def user_resource_kwargs(school):
	return {
		"properties": {
			"username": "test{}".format(random_name()),
			"password": random_name(),
			"firstname": random_name(),
			"lastname": random_name(),
			"birthday": "2015-05-15",
			"disabled": False,
			"groups": [
				"cn=DEMOSCHOOL-Da,cn=klassen,cn=schueler,cn=groups,ou={},{}".format(school, LDAP_BASE_DN),
				"cn=DEMOSCHOOL-Db,cn=klassen,cn=schueler,cn=groups,ou={},{}".format(school, LDAP_BASE_DN),
			],
		},
		"position": "cn=lehrer,cn=users,ou={},{}".format(school, LDAP_BASE_DN),
		"superordinate": None,
		"options": {"ucsschoolTeacher": True},
		"policies": {},
	}


def create_objs_via_UDM_HTTP_API_parallel(school, num, parallelism):
	# type: (str, int, int) -> Tuple[float, List[str]]
	# create `parallelism` amount of processes each working on a `num / parallelism` long list
	assert num % parallelism == 0
	if parallelism == 1:
		t0 = time.time()
		dns = []
		for _ in range(num):
			dns.extend(create_objs_via_UDM_HTTP_API_sequential([user_resource_kwargs(school)]))
		return time.time() - t0, dns
	kwargs = [[user_resource_kwargs(school) for i in range(int(num / parallelism))] for j in range(parallelism)]
	pool = Pool(processes=parallelism)
	t0 = time.time()
	map_async_result = pool.map_async(create_objs_via_UDM_HTTP_API_sequential, kwargs)
	results = map_async_result.get()
	t1 = time.time() - t0
	dns = []
	for res in results:
		dns.extend(res)
	return t1, dns


def read_objs_via_UDM_HTTP_API(dns):  # type: (List[str]) -> None
	headers = {"Accept": "application/json"}
	base_url = "{}/users/user/".format(BASE_URL)
	for dn in dns:
		obj_url = base_url + dn
		resp = requests.get(obj_url, headers=headers, auth=AUTH)
		if resp.status_code != 200:
			print("resp.status_code={!r}".format(resp.status_code))
			print("resp.text={!r}".format(resp.text))
			print("resp.json()={!r}".format(resp.json()))
			print("resp.headers={!r}".format(resp.headers))
			raise RuntimeError("Reading User failed.")
		assert resp.json()["dn"] == dn, "Wrong DN: {!r}".format(resp.json())


def read_objs_via_UDM_HTTP_API_parallel(dns, parallelism):  # type: (List[str], int) -> float
	# create `parallelism` amount of processes each working on a `num / parallelism` long list
	assert len(dns) % parallelism == 0
	if parallelism == 1:
		t0 = time.time()
		for dn in dns:
			read_objs_via_UDM_HTTP_API([dn])
		return time.time() - t0
	kwargs = [dns[i:i + parallelism] for i in range(0, len(dns), parallelism)]  # type: List[List[str]]
	pool = Pool(processes=parallelism)
	t0 = time.time()
	map_async_result = pool.map_async(read_objs_via_UDM_HTTP_API, kwargs)
	results = map_async_result.get()
	return time.time() - t0


def modify_objs_via_UDM_HTTP_API(school_dns):  # type: (Tuple[str, List[str]]) -> float
	school, dns = school_dns
	base_url = "{}/users/user/".format(BASE_URL)
	t_delta = 0.0
	for dn in dns:
		obj_url = base_url + dn
		headers = {"Accept": "application/json"}
		resp = requests.get(obj_url, headers=headers, auth=AUTH)
		if resp.status_code != 200:
			print("resp.status_code={!r}".format(resp.status_code))
			print("resp.text={!r}".format(resp.text))
			print("resp.json()={!r}".format(resp.json()))
			print("resp.headers={!r}".format(resp.headers))
			raise RuntimeError("Reading {} failed.".format(kls.__name__))
		obj_old = resp.json()
		data = {
			"position": obj_old["position"],
			"options": obj_old["options"],
			"policies": obj_old["policies"],
			"properties": {}
		}
		data["properties"] = {
			"firstname": random_name(),
			"lastname": random_name(),
		}
		t0 = time.time()
		resp = requests.patch(obj_url, headers=headers, json=data, auth=AUTH)
		t_delta += time.time() - t0
		if resp.status_code != 200:
			print("resp.status_code={!r}".format(resp.status_code))
			print("resp.text={!r}".format(resp.text))
			print("resp.json()={!r}".format(resp.json()))
			print("resp.headers={!r}".format(resp.headers))
			raise RuntimeError("Modification failed.")
		resp = requests.get(obj_url, headers=headers, auth=AUTH)
		if resp.status_code != 200:
			print("resp.status_code={!r}".format(resp.status_code))
			print("resp.text={!r}".format(resp.text))
			print("resp.json()={!r}".format(resp.json()))
			print("resp.headers={!r}".format(resp.headers))
			raise RuntimeError("Reading {} failed.".format(kls.__name__))
		obj_new = resp.json()
		assert obj_new["properties"]["firstname"] == data["properties"]["firstname"]
		assert obj_new["properties"]["lastname"] == data["properties"]["lastname"]
	return t_delta


def modify_objs_via_UDM_HTTP_API_parallel(school, dns, parallelism):  # type: (str, List[str], int) -> float
	assert len(dns) % parallelism == 0
	if parallelism == 1:
		t0 = time.time()
		for dn in dns:
			modify_objs_via_UDM_HTTP_API((school, [dn]))
		return time.time() - t0
	kwargs = [(school, dns[i:i + parallelism]) for i in range(0, len(dns), parallelism)]  # type: List[Tuple[str, List[str]]]
	pool = Pool(processes=parallelism)
	map_async_result = pool.map_async(modify_objs_via_UDM_HTTP_API, kwargs)
	results = map_async_result.get()
	return sum(results)


def delete_obj_via_UDM_HTTP_API(dns):   # type: (List[str]) -> None
	headers = {"Accept": "application/json"}
	for dn in dns:
		url = "{}/users/user/{}".format(BASE_URL, dn)
		resp = requests.delete(url, headers=headers, auth=AUTH)
		if resp.status_code != 200:
			print("resp.status_code={!r}".format(resp.status_code))
			print("resp.text={!r}".format(resp.text))
			print("resp.json()={!r}".format(resp.json()))
			print("resp.headers={!r}".format(resp.headers))
			raise RuntimeError("Deleting User failed.")


def delete_objs_via_UDM_HTTP_API_parallel(dns, parallelism):  # type: (List[str], int) -> float
	assert len(dns) % parallelism == 0
	if parallelism == 1:
		t0 = time.time()
		for dn in dns:
			delete_obj_via_UDM_HTTP_API([dn])
		return time.time() - t0
	kwargs = [dns[i:i + parallelism] for i in range(0, len(dns), parallelism)]  # type: List[List[str]]
	pool = Pool(processes=parallelism)
	t0 = time.time()
	map_async_result = pool.map_async(delete_obj_via_UDM_HTTP_API, kwargs)
	results = map_async_result.get()
	return time.time() - t0


def main():  # type: () -> None
	print("Starting HTTP tests (parallelism={})...".format(PARALLELISM))
	print("Connection args: {!r} {!r}".format(BASE_URL, AUTH))
	print("Creating 1000 Users...")
	t_1000_1, dns = create_objs_via_UDM_HTTP_API_parallel(SCHOOL_OU, 1000, PARALLELISM)
	time.sleep(30)

	print("Reading 1000 Users...")
	t_1000_2 = read_objs_via_UDM_HTTP_API_parallel(dns, PARALLELISM)

	print("Modifying 1000 Users...")
	t_1000_3 = modify_objs_via_UDM_HTTP_API_parallel(SCHOOL_OU, dns, PARALLELISM)
	time.sleep(15)

	print("Deleting 1000 Users...")
	t_1000_4 = delete_objs_via_UDM_HTTP_API_parallel(dns, PARALLELISM)

	print("Results:")
	print("Seconds for creating   1000 Users: {:02.2f}".format(t_1000_1))
	print("Seconds for reading    1000 Users: {:02.2f}".format(t_1000_2))
	print("Seconds for modifying  1000 Users: {:02.2f}".format(t_1000_3))
	print("Seconds for deleting   1000 Users: {:02.2f}".format(t_1000_4))


if __name__ == "__main__":
	main()
