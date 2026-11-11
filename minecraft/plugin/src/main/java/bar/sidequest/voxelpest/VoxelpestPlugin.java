package bar.sidequest.voxelpest;

import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.event.ClickEvent;
import net.kyori.adventure.text.event.HoverEvent;
import net.kyori.adventure.text.format.NamedTextColor;
import net.kyori.adventure.text.minimessage.MiniMessage;
import net.kyori.adventure.text.minimessage.tag.resolver.Placeholder;
import net.kyori.adventure.text.minimessage.tag.resolver.TagResolver;
import net.kyori.adventure.title.Title;
import org.bukkit.Bukkit;
import org.bukkit.Difficulty;
import org.bukkit.GameMode;
import org.bukkit.GameRule;
import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.WorldBorder;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.FileConfiguration;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerMoveEvent;
import org.bukkit.event.player.PlayerRespawnEvent;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.scheduler.BukkitTask;

import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.text.Normalizer;
import java.time.Duration;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

/** The SideQuest Bar's Budapest: a protected map with landmark teleports, flight and a status endpoint. */
public final class VoxelpestPlugin extends JavaPlugin implements Listener {

    record Landmark(String id, String name, double x, double y, double z, float yaw, float pitch, List<String> aliases) {
        Location at(World w) { return new Location(w, x, y, z, yaw, pitch); }
    }

    private final Map<String, Landmark> landmarks = new LinkedHashMap<>();
    private final Map<UUID, Long> edgeWarned = new HashMap<>();
    private final MiniMessage mm = MiniMessage.miniMessage();
    private Landmark mapSpawn;
    private double minX = Double.NEGATIVE_INFINITY, minZ = Double.NEGATIVE_INFINITY;
    private double maxX = Double.POSITIVE_INFINITY, maxZ = Double.POSITIVE_INFINITY;
    private String mapBuilt = "", mapVersion = "";
    private StatusServer status;
    private BukkitTask clock;
    /** /clock's held time in ticks (0 is 6:00), or null: config.yml's `time` rules. Kept in clock.yml. */
    private Long held;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        loadAll();
        loadHeld();
        getServer().getPluginManager().registerEvents(this, this);
        getServer().getPluginManager().registerEvents(new Protection(this), this);
        Bukkit.getScheduler().runTask(this, this::setUpWorld);   // after the worlds are loaded
        startStatus();
        watchForNewMap();
        Bukkit.getScheduler().runTaskTimerAsynchronously(this, this::pruneLogs, 200L, 20L * 3600 * 24);
        getLogger().info("Budapest: " + landmarks.size() + " landmarks, map built " + mapBuilt);
    }

    /**
     * The server's logs hold players' IP addresses, chat and commands. The privacy policy promises they go after
     * logs.keep-days (90): the rotated logs/*.log.gz older than that are deleted, at start and once a day. 0 keeps all.
     */
    private void pruneLogs() {
        int days = cfg().getInt("logs.keep-days", 90);
        File[] old = days <= 0 ? null : new File("logs").listFiles((d, n) -> n.endsWith(".log.gz"));
        if (old == null) return;
        long before = System.currentTimeMillis() - Duration.ofDays(days).toMillis();
        int n = 0;
        for (File f : old) if (f.lastModified() < before && f.delete()) n++;
        if (n > 0) getLogger().info("deleted " + n + " log file(s) older than " + days + " days");
    }

    // ------------------------------------------------------------------------------------------- map updates
    private boolean restarting;

    /**
     * The sync uploads a new map next to the server (map.yml last). When its build time differs from the one running,
     * the server warns the players and stops; Docker starts it again and start.sh swaps the world in.
     */
    private void watchForNewMap() {
        Bukkit.getScheduler().runTaskTimer(this, () -> {
            if (cfgFile != null && cfgFile.lastModified() != cfgStamp) {
                loadAll();
                setUpWorld();
                getLogger().info("settings reloaded from " + cfgFile);
            }
        }, 600L, 600L);
        String src = System.getenv("VOXELPEST_MAP_SOURCE");
        if (src == null || src.isBlank()) src = cfg().getString("update.source", "");
        if (src.isBlank() || !cfg().getBoolean("update.restart", true)) return;
        File f = new File(src);
        Bukkit.getScheduler().runTaskTimerAsynchronously(this, () -> {
            if (restarting || !f.isFile()) return;
            String built = YamlConfiguration.loadConfiguration(f).getString("built", "");
            if (!built.isEmpty() && !built.equals(mapBuilt)) Bukkit.getScheduler().runTask(this, () -> restartForUpdate(built));
        }, 600L, 600L);
    }

    private void restartForUpdate(String built) {
        if (restarting) return;
        restarting = true;
        int delay = Math.max(0, cfg().getInt("update.delay-seconds", 60));
        getLogger().info("new map (built " + built + "): restarting in " + (Bukkit.getOnlinePlayers().isEmpty() ? 0 : delay) + " s");
        if (Bukkit.getOnlinePlayers().isEmpty() || delay == 0) {
            Bukkit.shutdown();
            return;
        }
        String text = cfg().getString("messages.update", "");
        for (int left : new int[]{delay, 30, 10, 5}) {
            if (left > delay) continue;
            Bukkit.getScheduler().runTaskLater(this, () ->
                    Bukkit.broadcast(msg(text.replace("<seconds>", String.valueOf(left)))), (delay - left) * 20L);
        }
        Bukkit.getScheduler().runTaskLater(this, () -> {
            Component bye = msg(cfg().getString("messages.update-kick", "Budapest is being updated"));
            for (Player p : Bukkit.getOnlinePlayers()) p.kick(bye);
            Bukkit.shutdown();
        }, delay * 20L);
    }

    @Override
    public void onDisable() {
        if (status != null) status.stop();
        if (clock != null) clock.cancel();
    }

    // ------------------------------------------------------------------------------------------- settings and data
    private FileConfiguration cfg;
    private File cfgFile;
    private long cfgStamp;

    /** the settings: the project's config.yml uploaded next to the map ($VOXELPEST_CONFIG), else the plugin's own */
    FileConfiguration cfg() { return cfg; }

    private void loadConfigFile() {
        YamlConfiguration defaults = new YamlConfiguration();
        try (var in = getResource("config.yml")) {
            if (in != null) defaults = YamlConfiguration.loadConfiguration(new InputStreamReader(in, StandardCharsets.UTF_8));
        } catch (IOException ignored) { }
        String ext = System.getenv("VOXELPEST_CONFIG");
        cfgFile = ext != null && !ext.isBlank() && new File(ext).isFile() ? new File(ext) : new File(getDataFolder(), "config.yml");
        cfgStamp = cfgFile.lastModified();
        cfg = YamlConfiguration.loadConfiguration(cfgFile);
        cfg.setDefaults(defaults);
    }

    void loadAll() {
        loadConfigFile();
        landmarks.clear();
        File lf = new File(getDataFolder(), "landmarks.yml");
        if (lf.exists()) {
            ConfigurationSection s = YamlConfiguration.loadConfiguration(lf).getConfigurationSection("landmarks");
            if (s != null) {
                for (String id : s.getKeys(false)) {
                    ConfigurationSection l = s.getConfigurationSection(id);
                    if (l == null) continue;
                    landmarks.put(id.toLowerCase(Locale.ROOT), new Landmark(id.toLowerCase(Locale.ROOT), l.getString("name", id),
                            l.getDouble("x"), l.getDouble("y"), l.getDouble("z"),
                            (float) l.getDouble("yaw"), (float) l.getDouble("pitch"),
                            l.getStringList("aliases").stream().map(VoxelpestPlugin::fold).toList()));
                }
            }
        } else {
            getLogger().warning("no landmarks.yml in " + getDataFolder() + " (scripts/minecraft.py writes it)");
        }
        File mf = new File(getDataFolder(), "map.yml");
        if (mf.exists()) {
            YamlConfiguration m = YamlConfiguration.loadConfiguration(mf);
            double margin = cfg().getDouble("bounds-margin", 24);
            minX = m.getDouble("bounds.min-x") - margin;
            minZ = m.getDouble("bounds.min-z") - margin;
            maxX = m.getDouble("bounds.max-x") + margin;
            maxZ = m.getDouble("bounds.max-z") + margin;
            mapBuilt = m.getString("built", "");
            mapVersion = m.getString("minecraft", "");
            mapSpawn = new Landmark("map", "Spawn", m.getDouble("spawn.x"), m.getDouble("spawn.y"), m.getDouble("spawn.z"),
                    (float) m.getDouble("spawn.yaw"), (float) m.getDouble("spawn.pitch"), List.of());
        }
    }

    World world() {
        World w = Bukkit.getWorld(cfg().getString("world", "world"));
        return w != null ? w : Bukkit.getWorlds().get(0);
    }

    /** a setting from config.yml, unless the environment (start.sh, from .env) sets it */
    String setting(String path, String env) {
        String v = System.getenv(env);
        return v != null && !v.isBlank() ? v.trim() : cfg().getString(path, "");
    }

    boolean protecting() { return cfg().getBoolean("protect", true); }

    boolean builder(Player p) { return p.hasPermission("voxelpest.build"); }

    Location spawn() {
        Landmark l = landmarks.get(cfg().getString("spawn", "parliament").toLowerCase(Locale.ROOT));
        if (l == null) l = mapSpawn;
        if (l == null && !landmarks.isEmpty()) l = landmarks.values().iterator().next();
        return l != null ? l.at(world()) : world().getSpawnLocation();
    }

    private void setUpWorld() {
        World w = world();
        w.setDifficulty(Difficulty.PEACEFUL);
        w.setGameRule(GameRule.DO_MOB_SPAWNING, false);
        w.setGameRule(GameRule.SPAWN_MONSTERS, false);
        w.setGameRule(GameRule.DO_PATROL_SPAWNING, false);
        w.setGameRule(GameRule.DO_TRADER_SPAWNING, false);
        w.setGameRule(GameRule.DO_WARDEN_SPAWNING, false);
        w.setGameRule(GameRule.DO_INSOMNIA, false);
        w.setGameRule(GameRule.DO_FIRE_TICK, false);
        w.setGameRule(GameRule.MOB_GRIEFING, false);
        w.setGameRule(GameRule.TNT_EXPLODES, false);
        w.setGameRule(GameRule.RANDOM_TICK_SPEED, 0);      // no grass spreading or dying, no ice, no growth
        w.setGameRule(GameRule.DO_VINES_SPREAD, false);
        w.setGameRule(GameRule.DO_TILE_DROPS, false);
        w.setGameRule(GameRule.FALL_DAMAGE, false);
        w.setGameRule(GameRule.KEEP_INVENTORY, true);
        w.setGameRule(GameRule.ANNOUNCE_ADVANCEMENTS, false);
        w.setGameRule(GameRule.SPAWN_RADIUS, 0);
        w.setGameRule(GameRule.ALLOW_ENTERING_NETHER_USING_PORTALS, false);
        boolean cycle = held == null && "cycle".equalsIgnoreCase(cfg().getString("time", "real"));
        w.setGameRule(GameRule.DO_DAYLIGHT_CYCLE, cycle);
        if ("clear".equalsIgnoreCase(cfg().getString("weather", "clear"))) {
            w.setGameRule(GameRule.DO_WEATHER_CYCLE, false);
            w.setStorm(false);
            w.setThundering(false);
            w.setClearWeatherDuration(Integer.MAX_VALUE / 2);
        } else {
            w.setGameRule(GameRule.DO_WEATHER_CYCLE, true);
        }
        if (Double.isFinite(minX)) {  // a hard stop a little beyond the soft edge
            WorldBorder b = w.getWorldBorder();
            b.setCenter((minX + maxX) / 2, (minZ + maxZ) / 2);
            b.setSize(Math.max(maxX - minX, maxZ - minZ) + 64);
        }
        Location s = spawn();
        w.setSpawnLocation(s);
        if (clock != null) clock.cancel();
        clock = Bukkit.getScheduler().runTaskTimer(this, this::tick, 1L, 200L);
    }

    /** every 10 s: the sun follows Budapest's clock (or stays put), the status count */
    private void tick() {
        World w = world();
        String mode = cfg().getString("time", "real").toLowerCase(Locale.ROOT);
        if (held != null) {
            w.setTime(held);
        } else if (mode.equals("real")) {
            ZonedDateTime now = ZonedDateTime.now(ZoneId.of(cfg().getString("time-zone", "Europe/Budapest")));
            w.setTime(ticks(now.getHour(), now.getMinute()));
        } else if (mode.equals("day")) {
            w.setTime(3000);
        }
        if (status != null) status.update(Bukkit.getOnlinePlayers().size(), Bukkit.getMaxPlayers());
    }

    private void startStatus() {
        if (status != null) status.stop();
        status = null;
        if (!cfg().getBoolean("status.enabled", true)) return;
        try {
            status = new StatusServer(cfg().getString("status.bind", "0.0.0.0"), cfg().getInt("status.port", 8765),
                    setting("status.address", "VOXELPEST_ADDRESS"), Bukkit.getMinecraftVersion(), () -> mapBuilt);
            status.update(Bukkit.getOnlinePlayers().size(), Bukkit.getMaxPlayers());
            Bukkit.getScheduler().runTaskTimer(this, () -> status.update(Bukkit.getOnlinePlayers().size(), Bukkit.getMaxPlayers()), 20L, 20L);
        } catch (Exception e) {
            getLogger().warning("status endpoint not started: " + e.getMessage());
        }
    }

    // ------------------------------------------------------------------------------------------- messages
    Component msg(String text) {
        TagResolver links = TagResolver.resolver(
                Placeholder.parsed("map", setting("links.map", "VOXELPEST_MAP_URL")),
                Placeholder.parsed("bar", setting("links.bar", "VOXELPEST_BAR_URL")),
                Placeholder.parsed("terms", cfg().getString("links.terms", "https://side-quest.bar/terms")),
                Placeholder.parsed("privacy", cfg().getString("links.privacy", "https://side-quest.bar/privacy")));
        return mm.deserialize(text, links);
    }

    private void sendLines(CommandSender to, String key) {
        if (cfg().isList(key)) {
            for (String line : cfg().getStringList(key)) to.sendMessage(msg(line));
        } else if (cfg().isString(key)) {
            to.sendMessage(msg(cfg().getString(key)));
        }
    }

    // ------------------------------------------------------------------------------------------- players
    @EventHandler
    public void onJoin(PlayerJoinEvent e) {
        Player p = e.getPlayer();
        if (protecting() && !builder(p)) p.setGameMode(GameMode.ADVENTURE);
        if (cfg().getBoolean("fly-on-join", true) && p.hasPermission("voxelpest.fly")) p.setAllowFlight(true);
        p.setFlySpeed(speed(cfg().getInt("fly-speed", 3)));
        if (!p.hasPlayedBefore() || outside(p.getLocation())) {
            p.teleportAsync(spawn()).thenRun(() -> Bukkit.getScheduler().runTask(this, () -> airborne(p)));
        }
        p.showTitle(Title.title(msg(cfg().getString("messages.title", "")), msg(cfg().getString("messages.subtitle", "")),
                Title.Times.times(Duration.ofMillis(500), Duration.ofSeconds(4), Duration.ofSeconds(1))));
        p.sendPlayerListHeaderAndFooter(msg(cfg().getString("messages.tab-header", "")),
                msg(cfg().getString("messages.tab-footer", "")));
        sendLines(p, "messages.welcome");
    }

    @EventHandler
    public void onRespawn(PlayerRespawnEvent e) {
        e.setRespawnLocation(spawn());
    }

    private boolean outside(Location l) {
        return l.getX() < minX || l.getX() > maxX || l.getZ() < minZ || l.getZ() > maxZ || l.getY() < -60;
    }

    @EventHandler(ignoreCancelled = true)
    public void onMove(PlayerMoveEvent e) {
        Location to = e.getTo();
        if (e.getFrom().getBlockX() == to.getBlockX() && e.getFrom().getBlockZ() == to.getBlockZ()
                && e.getFrom().getBlockY() == to.getBlockY()) return;
        if (!outside(to)) return;
        Player p = e.getPlayer();
        if (to.getY() < -60) {
            p.teleportAsync(spawn());
            return;
        }
        Location back = to.clone();
        back.setX(Math.max(minX + 1, Math.min(maxX - 1, to.getX())));
        back.setZ(Math.max(minZ + 1, Math.min(maxZ - 1, to.getZ())));
        e.setTo(back);
        long now = System.currentTimeMillis();
        if (now - edgeWarned.getOrDefault(p.getUniqueId(), 0L) > 3000) {
            edgeWarned.put(p.getUniqueId(), now);
            p.sendActionBar(msg(cfg().getString("messages.edge", "")));
        }
    }

    /** after a teleport into the air: start flying instead of falling */
    private void airborne(Player p) {
        if (!p.isOnline() || !p.getAllowFlight()) return;
        if (p.getLocation().clone().subtract(0, 1, 0).getBlock().isEmpty()) p.setFlying(true);
    }

    private static float speed(int n) {
        return Math.max(1, Math.min(10, n)) / 10f;
    }

    // ------------------------------------------------------------------------------------------- commands
    @Override
    public boolean onCommand(CommandSender sender, Command cmd, String label, String[] args) {
        switch (cmd.getName().toLowerCase(Locale.ROOT)) {
            case "lm" -> {
                if (args.length == 0) { listLandmarks(sender); return true; }
                if (!(sender instanceof Player p)) { sender.sendMessage("Players only."); return true; }
                Landmark l = find(String.join(" ", args));
                if (l == null) {
                    sender.sendMessage(Component.text("No landmark like that. ", NamedTextColor.GRAY).append(
                            Component.text("/lm", NamedTextColor.YELLOW).clickEvent(ClickEvent.runCommand("/lm"))));
                    return true;
                }
                p.teleportAsync(l.at(world())).thenRun(() -> Bukkit.getScheduler().runTask(this, () -> airborne(p)));
                p.sendActionBar(Component.text(l.name(), NamedTextColor.GOLD));
                return true;
            }
            case "spawn" -> {
                if (sender instanceof Player p) p.teleportAsync(spawn()).thenRun(() -> Bukkit.getScheduler().runTask(this, () -> airborne(p)));
                return true;
            }
            case "fly" -> {
                if (!(sender instanceof Player p)) return true;
                boolean on = !p.getAllowFlight();
                p.setAllowFlight(on);
                if (on) {
                    p.setFlying(true);
                    p.sendActionBar(Component.text("Flying: on (double-jump to take off and land)", NamedTextColor.GREEN));
                } else {
                    p.setFlying(false);
                    p.sendActionBar(Component.text("Flying: off", NamedTextColor.GRAY));
                }
                return true;
            }
            case "flyspeed" -> {
                if (!(sender instanceof Player p)) return true;
                try {
                    int n = Integer.parseInt(args[0]);
                    p.setFlySpeed(speed(n));
                    p.sendActionBar(Component.text("Flying speed " + Math.max(1, Math.min(10, n)), NamedTextColor.GREEN));
                } catch (Exception ex) {
                    sender.sendMessage(Component.text("/flyspeed 1-10 (now " + Math.round(p.getFlySpeed() * 10) + ")", NamedTextColor.GRAY));
                }
                return true;
            }
            case "map" -> { sendLines(sender, "messages.map"); return true; }
            case "terms" -> { sendLines(sender, "messages.terms"); return true; }
            case "bar" -> {
                // straight to the bar's door (the street-level teleport scripts/minecraft.py writes), then what it is
                Landmark l = landmarks.getOrDefault("bar", landmarks.get("sidequest"));
                if (sender instanceof Player p && l != null) {
                    p.teleportAsync(l.at(world())).thenRun(() -> Bukkit.getScheduler().runTask(this, () -> airborne(p)));
                    p.sendActionBar(Component.text("SideQuest Bar", NamedTextColor.GOLD));
                }
                sendLines(sender, "messages.bar");
                return true;
            }
            case "voxelpest" -> {
                if (args.length > 0 && args[0].equalsIgnoreCase("reload")) {
                    loadAll();
                    setUpWorld();
                    startStatus();
                    sender.sendMessage(Component.text("Budapest: " + landmarks.size() + " landmarks, map built " + mapBuilt, NamedTextColor.GREEN));
                } else {
                    sender.sendMessage(Component.text("Budapest map built " + mapBuilt + " for " + mapVersion + ", " + landmarks.size()
                            + " landmarks. /voxelpest reload", NamedTextColor.GRAY));
                }
                return true;
            }
            case "clock" -> {
                if (args.length == 0) {
                    String mode = cfg().getString("time", "real");
                    sender.sendMessage(Component.text(held != null
                            ? "Held at " + clockText(held) + " (/clock live gives it back to config.yml's time: " + mode + ")"
                            : "Following config.yml's time: " + mode + " (now " + clockText(world().getTime()) + ")",
                            NamedTextColor.GRAY));
                    return true;
                }
                String a = args[0].toLowerCase(Locale.ROOT);
                if (a.equals("live") || a.equals("release") || a.equals("off")) {
                    held = null;
                    saveHeld();
                    setUpWorld();  // the daylight rule back to config.yml's, and the clock ticks at once
                    sender.sendMessage(Component.text("Clock: config.yml's time again (" + cfg().getString("time", "real") + ")", NamedTextColor.GREEN));
                    return true;
                }
                Long t = parseClock(a);
                if (t == null) {
                    sender.sendMessage(Component.text("/clock HH:MM | ticks (0-23999, 0 is 6:00) | noon | midnight | live", NamedTextColor.GRAY));
                    return true;
                }
                held = t;
                saveHeld();
                setUpWorld();
                sender.sendMessage(Component.text("Clock held at " + clockText(t) + " until /clock live", NamedTextColor.GREEN));
                return true;
            }
            default -> { return false; }
        }
    }

    // ------------------------------------------------------------------------------------------- /clock
    /** a clock time as Minecraft ticks: 0 is 6:00, 6000 noon, 18000 midnight */
    private static long ticks(int hour, int minute) {
        return (((hour - 6 + 24) % 24) * 1000L + minute * 1000L / 60) % 24000L;
    }

    private static String clockText(long t) {
        long m = ((t % 24000 + 24000) % 24000 * 60 / 1000 + 6 * 60) % (24 * 60);
        return String.format(Locale.ROOT, "%02d:%02d", m / 60, m % 60);
    }

    /** "21:30", "9", "noon", "midnight" or ticks ("18000"); null if it's none of them */
    private static Long parseClock(String s) {
        switch (s) {
            case "noon" -> { return ticks(12, 0); }
            case "midnight" -> { return ticks(0, 0); }
            case "sunrise" -> { return 23000L; }
            case "sunset" -> { return 12000L; }
            default -> { }
        }
        try {
            if (s.contains(":")) {
                String[] p = s.split(":", 2);
                int h = Integer.parseInt(p[0]), m = Integer.parseInt(p[1]);
                return h >= 0 && h < 24 && m >= 0 && m < 60 ? ticks(h, m) : null;
            }
            int n = Integer.parseInt(s);
            if (s.length() <= 2) return n >= 0 && n < 24 ? ticks(n, 0) : null;  // an hour
            return n >= 0 && n < 24000 ? (long) n : null;                       // ticks
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private File heldFile() { return new File(getDataFolder(), "clock.yml"); }

    private void loadHeld() {
        File f = heldFile();
        held = null;
        if (!f.isFile()) return;
        YamlConfiguration y = YamlConfiguration.loadConfiguration(f);
        if (y.isLong("held") || y.isInt("held")) held = Math.floorMod(y.getLong("held"), 24000L);
        if (held != null) getLogger().info("clock held at " + clockText(held) + " (/clock live to release)");
    }

    private void saveHeld() {
        File f = heldFile();
        if (held == null) {
            if (f.exists() && !f.delete()) getLogger().warning("could not delete " + f);
            return;
        }
        YamlConfiguration y = new YamlConfiguration();
        y.set("held", held);
        try {
            y.save(f);
        } catch (IOException e) {
            getLogger().warning("could not save " + f + ": " + e.getMessage());
        }
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command cmd, String label, String[] args) {
        if (cmd.getName().equalsIgnoreCase("lm") && args.length == 1) {
            String a = fold(args[0]);
            List<String> out = new ArrayList<>();
            for (String id : landmarks.keySet()) if (id.startsWith(a)) out.add(id);
            return out;
        }
        if (cmd.getName().equalsIgnoreCase("flyspeed") && args.length == 1) return List.of("1", "2", "3", "5", "7", "10");
        if (cmd.getName().equalsIgnoreCase("voxelpest") && args.length == 1) return List.of("reload");
        if (cmd.getName().equalsIgnoreCase("clock") && args.length == 1) {
            List<String> out = new ArrayList<>();
            for (String s : List.of("live", "noon", "midnight", "sunrise", "sunset", "08:00", "18:30", "21:00"))
                if (s.startsWith(args[0].toLowerCase(Locale.ROOT))) out.add(s);
            return out;
        }
        return List.of();
    }

    private static String fold(String s) {  // "Hősök tere" -> "hosok tere"
        return Normalizer.normalize(s, Normalizer.Form.NFD).replaceAll("\\p{M}", "").replaceAll("[-'’_]", " ")
                .replaceAll("\\s+", " ").toLowerCase(Locale.ROOT).trim();
    }

    private Landmark find(String q) {
        String f = fold(q);
        Landmark l = landmarks.get(f);
        if (l != null) return l;
        if (f.isEmpty()) return null;
        for (Landmark x : landmarks.values()) if (x.aliases().contains(f)) return x;
        for (Landmark x : landmarks.values()) if (x.id().startsWith(f)) return x;
        for (Landmark x : landmarks.values()) if (x.aliases().stream().anyMatch(a -> a.startsWith(f))) return x;
        for (Landmark x : landmarks.values()) if (fold(x.name()).contains(f)) return x;
        for (Landmark x : landmarks.values()) if (x.aliases().stream().anyMatch(a -> a.contains(f))) return x;
        return null;
    }

    private void listLandmarks(CommandSender to) {
        Component line = Component.text("Landmarks ", NamedTextColor.GOLD)
                .append(Component.text("(click one, or /lm <name>): ", NamedTextColor.GRAY));
        boolean first = true;
        for (Landmark l : landmarks.values()) {
            if (!first) line = line.append(Component.text(" · ", NamedTextColor.DARK_GRAY));
            first = false;
            line = line.append(Component.text(l.id(), NamedTextColor.YELLOW)
                    .hoverEvent(HoverEvent.showText(Component.text(l.name())))
                    .clickEvent(ClickEvent.runCommand("/lm " + l.id())));
        }
        to.sendMessage(line);
    }
}
