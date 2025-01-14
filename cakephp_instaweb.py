# -*- coding: utf-8 -*-
"""
  cakephp_instaweb

  Copyright (C) 2007, 2009 Chris Lamb <chris@chris-lamb.co.uk>

  Permission is hereby granted, free of charge, to any person obtaining a
  copy of this software and associated documentation files (the "Software"),
  to deal in the Software without restriction, including without limitation
  the rights to use, copy, modify, merge, publish, distribute, sublicense,
  and/or sell copies of the Software, and to permit persons to whom the
  Software is furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in
  all copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
  DEALINGS IN THE SOFTWARE.
"""

from twisted.internet import reactor, error
from twisted.web import static, server, twcgi, rewrite

from optparse import OptionParser
from os.path import exists, dirname, join

import os
import sys
import time

def main():
    options = parse_options()

    class PHPScript(twcgi.FilteredScript):
        filter = find_php()

        def runProcess(self, env, request, qargs=[]):
            env['REDIRECT_STATUS'] = '200'
            twcgi.FilteredScript.runProcess(self, env, request, qargs)

    root = static.File(options.webroot)
    root.processors = {'.php' : PHPScript}
    root.indexNames = ['index.php']

    def rewrite_rule(request):
        # Emulate Apache's mod_rewrite - if the file does not exist, then
        # rewrite as a suffix to '/index.php?url=' if major is not '2'
        if not os.access("%s/%s" % (options.webroot, request.path), os.F_OK):
            if options.major == '2.0':
                pass
            else:
                request.uri = "/index.php?url=%s" % request.path
            request.postpath = ['index.php']
        return request

    def logger_rule(request):
        print '[%s] "%s %s"' % \
            (time.strftime("%d/%b/%Y %H:%M:%S"), request.method, request.path)

    if options.rewrite:
        root = rewrite.RewriterResource(root, rewrite_rule)
    if not options.quiet:
        root = rewrite.RewriterResource(root, logger_rule)

    try:
        reactor.listenTCP(
            options.port,
            server.Site(root),
            interface=options.interface,
        )
    except error.CannotListenError, e:
        print >>sys.stderr, "%s: Couldn't listen on port %d: %s" % \
            (sys.argv[0], options.port, e.socketError[1])
        sys.exit(-1)

    if not options.quiet:
        print >>sys.stderr, """
        CakePHP development server is running at http://localhost:%d/
        Quit the server with CONTROL-C.
        """ % options.port

    reactor.run()

def parse_options():
    usage = "%prog [webroot]"
    parser = OptionParser(usage=usage)
    parser.add_option("-p", "--port", dest="port", type="int",
        help="serve on port PORT (default: 3000)",
        metavar="PORT", default="3000")
    parser.add_option("-i", "--interface", dest="interface",
        help="interface to serve from (default: 127.0.0.1)",
        default="127.0.0.1")
    parser.add_option("-m", "--major-release", dest="major",
        help="CakePHP major release (default: 1.0)",
        default="1.0")
    parser.add_option("-r", "--disable-rewrite", dest="rewrite",
        help="disable URL rewriting", action="store_false",
        default=True)
    parser.add_option("-q", "--quiet", dest="quiet",
        help="quiet mode", action="store_true",
        default=False)

    options, args = parser.parse_args()

    if len(args) == 0:
        options.webroot = find_webroot()
    elif len(args) == 1:
        options.webroot = args[0]
    else:
        parser.error('incorrect number of arguments')

    return options

def find_webroot():

    # Descend
    search = ['src', 'app', 'webroot']
    for i in range(len(search)):
        path = join(*[os.getcwd()] + search[i:])
        if exists(join(path, 'index.php')): return path

    # Ascend
    search = os.getcwd()
    while len(search) > 1:
        path = join(search, 'webroot')
        search = dirname(search)
        if exists(join(path, 'index.php')): return path

    print >>sys.stderr, "%s: cannot find a CakePHP application; exiting." % \
        sys.argv[0]
    sys.exit(-1)

def find_php():
    paths = (
        '/etc/alternatives',
        '/usr/bin',
        '/usr/local/bin',
        '/usr/sbin',
        '/usr/local/sbin',
        '/opt/php',
    )

    binaries = (
        'php-cgi',
        'php5-cgi',
        'php4-cgi',
        'php',
        'php5',
        'php4',
    )

    for php_path, binary in [(x, y) for x in paths for y in binaries]:
        candidate = join(php_path, binary)
        if exists(candidate):
            return candidate

    print >>sys.stderr, "%s: cannot find a PHP binary application; exiting." % \
        sys.argv[0]
    sys.exit(-1)

if __name__ == "__main__":
    main()
