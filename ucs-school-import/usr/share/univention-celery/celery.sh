# Univention Celery Shell Library
#
# SPDX-FileCopyrightText: 2017-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

rabbitmq_add_vhost() {
	local username="${1:?Usage: rabbitmq_add_vhost <username> <password> <vhost_name>}"
	local password="${2:?Usage: rabbitmq_add_vhost <username> <password> <vhost_name>}"
	local vhost_name="${3:?Usage: rabbitmq_add_vhost <username> <password> <vhost_name>}"

	rabbitmqctl add_user "$username" "$password"
	rabbitmqctl add_vhost "$vhost_name"
	rabbitmqctl set_permissions -p "$vhost_name" "$username" ".*" ".*" ".*"
}

rabbitmq_remove_vhost() {
	local username="${1:?Usage: rabbitmq_remove_vhost <username> <vhost_name>}"
	local vhost_name="${2:?Usage: rabbitmq_remove_vhost <username> <vhost_name>}"

	rabbitmqctl delete_vhost "$vhost_name"
	rabbitmqctl delete_user "$username"
}
