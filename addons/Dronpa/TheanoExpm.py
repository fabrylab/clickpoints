import theano
import scipy
import theano.tensor as T
import numpy as np

theano.config.compute_test_value = 'off'

class Expm(theano.Op):
    __props__ = ()

    def make_node(self, x):
        # check that the theano version has support for __props__
        assert hasattr(self, '_props')
        x = theano.tensor.as_tensor_variable(x)
        return theano.Apply(self, [x], [x.type()])

    def perform(self, node, inputs, output_storage):
        x = inputs[0]
        z = output_storage[0]
        try:
            z[0] = scipy.linalg.expm(x)
        except:
            z[0] = x*np.nan

    def grad(self, inputs, output_grads):
        """ Source: http://www.phantag.com/?p=16002
        """

        N = inputs[0].shape[0]
        A = inputs[0]
        B = T.concatenate((  T.concatenate(( A, T.zeros(A.shape) ), 1),
                             T.concatenate(( T.zeros(A.shape), A ), 1)  ))

        def GetJacobi(i, B):
            y,x = T.int_div(i, N),T.mod(i,N)#divmod(i,N)
            B = T.set_subtensor(B[y,N+x], 1)
            B2 = self( B )
            B = T.set_subtensor(B[y,N+x], 0)
            return B2[:N,N:].reshape((N*N,))
        J, updates = theano.scan(fn=GetJacobi, outputs_info=None, non_sequences=B,  sequences=theano.tensor.arange(999999), n_steps=(N*N))
        return [T.dot(J, output_grads[0].reshape( (N*N,) )).reshape( (N,N) )]

        """
        J = T.zeros((N*N,N*N))
        for i in xrange(N*N):
            y,x = divmod(i,N)
            B = T.set_subtensor(B[y,N+x], 1)
            B2 = self( B )
            B = T.set_subtensor(B[y,N+x], 0)
            J = T.set_subtensor(J[i,:], B2[:N,N:].reshape((N*N,)))
        return [T.dot(J, output_grads[0].reshape( (N*N,) )).reshape( (N,N) )]
        """

    def infer_shape(self, node, i0_shapes):
        return i0_shapes

if __name__ == "__main__":
    x = theano.tensor.matrix()
    f = theano.function([x], Expm()(x))
    import numpy
    inp = ( numpy.random.rand(5, 5) ).astype(numpy.float32)
    inp[0,0] = np.nan
    out = f(inp)
    #assert numpy.allclose(scipy.linalg.expm(inp), out)
    print(inp)
    print(out)

    print("Testing Gradient")
    print(theano.tests.unittest_tools.verify_grad(Expm(), [numpy.random.rand(6, 6)*100]))
