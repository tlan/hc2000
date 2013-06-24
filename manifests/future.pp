file { '/etc/future.txt':
    ensure  => file,
    content => '
    It is the future,
    The distant future
    It is the distant future,
    The year 2000

',
}
