package demo.server;

public final class WorldStartup {
    private final WorldDatabase database;
    private final PacketRegistry packets;

    public WorldStartup(WorldDatabase database, PacketRegistry packets) {
        this.database = database;
        this.packets = packets;
    }

    public void start() {
        database.connect();
        database.runMigrations();
        packets.registerLoginPackets();
        packets.registerChannelPackets();
    }
}
