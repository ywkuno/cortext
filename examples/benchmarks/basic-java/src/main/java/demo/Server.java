package demo;

public final class Server {
    private final WorldLoader worldLoader;

    public Server(WorldLoader worldLoader) {
        this.worldLoader = worldLoader;
    }

    public void boot() {
        worldLoader.loadDatabases();
        worldLoader.loadPackets();
        worldLoader.startChannels();
    }

    public static void main(String[] args) {
        new Server(new WorldLoader()).boot();
    }
}
