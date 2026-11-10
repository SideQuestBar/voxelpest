package bar.sidequest.voxelpest;

import org.bukkit.entity.Entity;
import org.bukkit.entity.Player;
import org.bukkit.event.Cancellable;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.Action;
import org.bukkit.event.block.BlockBreakEvent;
import org.bukkit.event.block.BlockBurnEvent;
import org.bukkit.event.block.BlockDamageEvent;
import org.bukkit.event.block.BlockExplodeEvent;
import org.bukkit.event.block.BlockFadeEvent;
import org.bukkit.event.block.BlockFertilizeEvent;
import org.bukkit.event.block.BlockFormEvent;
import org.bukkit.event.block.BlockFromToEvent;
import org.bukkit.event.block.BlockGrowEvent;
import org.bukkit.event.block.BlockIgniteEvent;
import org.bukkit.event.block.BlockPistonExtendEvent;
import org.bukkit.event.block.BlockPistonRetractEvent;
import org.bukkit.event.block.BlockPlaceEvent;
import org.bukkit.event.block.BlockSpreadEvent;
import org.bukkit.event.block.FluidLevelChangeEvent;
import org.bukkit.event.block.LeavesDecayEvent;
import org.bukkit.event.block.MoistureChangeEvent;
import org.bukkit.event.block.SpongeAbsorbEvent;
import org.bukkit.event.entity.CreatureSpawnEvent;
import org.bukkit.event.entity.EntityChangeBlockEvent;
import org.bukkit.event.entity.EntityDamageEvent;
import org.bukkit.event.entity.EntityExplodeEvent;
import org.bukkit.event.entity.FoodLevelChangeEvent;
import org.bukkit.event.hanging.HangingBreakByEntityEvent;
import org.bukkit.event.hanging.HangingBreakEvent;
import org.bukkit.event.hanging.HangingPlaceEvent;
import org.bukkit.event.player.PlayerArmorStandManipulateEvent;
import org.bukkit.event.player.PlayerBucketEmptyEvent;
import org.bukkit.event.player.PlayerBucketFillEvent;
import org.bukkit.event.player.PlayerDropItemEvent;
import org.bukkit.event.player.PlayerInteractEntityEvent;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.event.world.StructureGrowEvent;

/** Nothing in the city changes unless a builder (voxelpest.build) does it. */
final class Protection implements Listener {
    private final VoxelpestPlugin plugin;

    Protection(VoxelpestPlugin plugin) { this.plugin = plugin; }

    private boolean on() { return plugin.protecting(); }

    /** cancel unless the one responsible is a builder */
    private void guard(Cancellable e, Entity who) {
        if (!on()) return;
        if (who instanceof Player p && plugin.builder(p)) return;
        e.setCancelled(true);
    }

    private void stop(Cancellable e) {
        if (on()) e.setCancelled(true);
    }

    // players
    @EventHandler(priority = EventPriority.LOWEST) public void on(BlockBreakEvent e) { guard(e, e.getPlayer()); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(BlockDamageEvent e) { guard(e, e.getPlayer()); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(BlockPlaceEvent e) { guard(e, e.getPlayer()); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(PlayerBucketEmptyEvent e) { guard(e, e.getPlayer()); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(PlayerBucketFillEvent e) { guard(e, e.getPlayer()); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(HangingPlaceEvent e) { guard(e, e.getPlayer()); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(PlayerArmorStandManipulateEvent e) { guard(e, e.getPlayer()); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(PlayerInteractEntityEvent e) { guard(e, e.getPlayer()); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(PlayerDropItemEvent e) { guard(e, e.getPlayer()); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(BlockFertilizeEvent e) { guard(e, e.getPlayer()); }

    @EventHandler(priority = EventPriority.LOWEST)
    public void on(HangingBreakEvent e) {
        if (e instanceof HangingBreakByEntityEvent b) guard(e, b.getRemover());
        else stop(e);
    }

    @EventHandler(priority = EventPriority.LOWEST)
    public void on(PlayerInteractEvent e) {
        if (!on() || plugin.builder(e.getPlayer())) return;
        if (e.getAction() == Action.PHYSICAL) { e.setCancelled(true); return; }  // trampling, pressure plates
        if (e.getAction() == Action.RIGHT_CLICK_BLOCK && e.getClickedBlock() != null
                && e.getClickedBlock().getType().isInteractable()) e.setCancelled(true);  // doors, buttons, levers
    }

    // the world on its own: fire, liquids, decay, growth, explosions
    @EventHandler(priority = EventPriority.LOWEST) public void on(BlockBurnEvent e) { stop(e); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(BlockIgniteEvent e) { guard(e, e.getPlayer()); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(BlockSpreadEvent e) { stop(e); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(BlockFadeEvent e) { stop(e); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(BlockFormEvent e) { stop(e); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(BlockGrowEvent e) { stop(e); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(BlockFromToEvent e) { stop(e); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(FluidLevelChangeEvent e) { stop(e); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(LeavesDecayEvent e) { stop(e); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(MoistureChangeEvent e) { stop(e); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(SpongeAbsorbEvent e) { stop(e); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(StructureGrowEvent e) { stop(e); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(BlockPistonExtendEvent e) { stop(e); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(BlockPistonRetractEvent e) { stop(e); }
    @EventHandler(priority = EventPriority.LOWEST) public void on(EntityChangeBlockEvent e) { guard(e, e.getEntity()); }

    @EventHandler(priority = EventPriority.LOWEST)
    public void on(BlockExplodeEvent e) {
        if (on()) e.blockList().clear();
    }

    @EventHandler(priority = EventPriority.LOWEST)
    public void on(EntityExplodeEvent e) {
        if (on()) e.blockList().clear();
    }

    // nobody gets hurt, hungry or chased
    @EventHandler(priority = EventPriority.LOWEST)
    public void on(EntityDamageEvent e) {
        if (on() && e.getEntity() instanceof Player) e.setCancelled(true);
    }

    @EventHandler(priority = EventPriority.LOWEST)
    public void on(FoodLevelChangeEvent e) {
        if (on() && e.getFoodLevel() < e.getEntity().getFoodLevel()) e.setCancelled(true);
    }

    @EventHandler(priority = EventPriority.LOWEST)
    public void on(CreatureSpawnEvent e) {
        if (!on()) return;
        switch (e.getSpawnReason()) {
            case CUSTOM, COMMAND, SPAWNER_EGG -> { }
            default -> e.setCancelled(true);
        }
    }
}
