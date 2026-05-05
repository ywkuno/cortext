package demo.server;

public final class WorldDatabase {
    public void connect() {
        System.out.println("connect");
    }

    public void runMigrations() {
        System.out.println("migrate");
    }
}
