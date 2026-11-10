package bar.sidequest.voxelpest;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.Executors;
import java.util.function.Supplier;

/**
 * GET /status -> {"online":3,"max":50,"version":"26.3","address":"mc.side-quest.bar","built":"..."} with CORS, for the
 * web map's "Play in Minecraft" button. Counts only, no player names. The counts are set from the main thread.
 */
final class StatusServer {
    private final HttpServer http;
    private final String version, address;
    private final Supplier<String> built;
    private volatile int online, max;

    StatusServer(String bind, int port, String address, String version, Supplier<String> built) throws IOException {
        this.address = address;
        this.version = version;
        this.built = built;
        http = HttpServer.create(new InetSocketAddress(bind, port), 16);
        http.createContext("/", this::handle);
        http.setExecutor(Executors.newSingleThreadExecutor(r -> {
            Thread t = new Thread(r, "voxelpest-status");
            t.setDaemon(true);
            return t;
        }));
        http.start();
    }

    void update(int online, int max) {
        this.online = online;
        this.max = max;
    }

    void stop() {
        http.stop(0);
    }

    private static String quote(String s) {
        return "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
    }

    private void handle(HttpExchange ex) throws IOException {
        try (ex) {
            var h = ex.getResponseHeaders();
            h.set("Access-Control-Allow-Origin", "*");
            h.set("Access-Control-Allow-Methods", "GET, OPTIONS");
            h.set("Cache-Control", "no-cache, max-age=0");
            String path = ex.getRequestURI().getPath();
            String method = ex.getRequestMethod();
            if (method.equals("OPTIONS")) {
                ex.sendResponseHeaders(204, -1);
                return;
            }
            if (!(method.equals("GET") || method.equals("HEAD")) || !(path.equals("/") || path.equals("/status"))) {
                ex.sendResponseHeaders(404, -1);
                return;
            }
            byte[] body = ("{\"online\":" + online + ",\"max\":" + max + ",\"version\":" + quote(version)
                    + ",\"address\":" + quote(address) + ",\"built\":" + quote(built.get()) + "}")
                    .getBytes(StandardCharsets.UTF_8);
            h.set("Content-Type", "application/json; charset=utf-8");
            if (method.equals("HEAD")) {
                ex.sendResponseHeaders(200, -1);
                return;
            }
            ex.sendResponseHeaders(200, body.length);
            try (OutputStream o = ex.getResponseBody()) {
                o.write(body);
            }
        }
    }
}
