#puppet

file { '/etc/future.txt':
    ensure  => file,
    content => '
    It is the future,
    The distant future
    It is the distant future,
    The year 2000

        - in The Humans are Dead,
          by Flight of the Conchords
',
}
