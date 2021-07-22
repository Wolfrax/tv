import matplotlib
import ws

# This is for testing purposes only

if __name__ == "__main__":
    matplotlib.rcParams['timezone'] = '+2:00'

    m = ws.Measurements()
    g = ws.Graph()
    g.plot(m.data)
    g.show()
    g.close()
