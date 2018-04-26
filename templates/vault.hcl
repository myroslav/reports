storage "file" {
	path = "{{parts.buildout.directory}}/var/vault/vault"
}

listener "tcp" {
	address = "{{ address }}"
	tls_disable = {{ disable_tls }}
}

disable_mlock = true
