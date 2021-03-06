import numpy as np

def open_file(name_or_obj,mode='rb'):
    """return an open file object from a filename or open file object

    If a new file object was opened, it the return variable close_file
    will be True.
    """
    fd = name_or_obj
    close_file = False
    if isinstance(fd,basestring):
        fd = open(fd,mode=mode)
        close_file = True
    return fd, close_file

def load_dat_file(fd):
    """read a .dat file and return an array

    Parameters
    ----------
    fd : string or file
        If fd is a string, it is treated as a filename. Otherwise, fd
        is treated as an open file object.

    Returns
    -------
    M : a numpy array
    """
    fd,close_file = open_file(fd,mode='rb')
    buf = fd.read()
    if close_file:
        fd.close()
    lines = buf.split('\n')[:-1]
    return np.array([map(float,line.split()) for line in lines])

def save_dat_file(M,fd,isint=False):
    """write an array to a .dat file

    Parameters
    ----------
    M : array_like
        M may be 2 dimensional, or 1 dimensional. If M is 1
        dimensional, it is converted to a 1xN array before being
        saved.
    fd : string or file
        If fd is a string, it is treated as a filename. Otherwise, fd
        is treated as an open file object.

    Other Parameters
    ----------------
    isint : boolean
        Set to True to treat array as integer array. Defaults to
        False.
    """
    def fmt(f):
        if isint:
            return '%d'%f
        else:
            return '% 8e'%f
    A = np.asarray(M)
    if len(A.shape) == 1:
        A=np.reshape(A, (1,A.shape[0]) )

    fd,close_file = open_file(fd,mode='wb')
    for i in range(A.shape[0]):
        buf = ' '.join( map( fmt, A[i,:] ) )
        fd.write( buf )
        fd.write( '\n' )
    if close_file:
        fd.close()
