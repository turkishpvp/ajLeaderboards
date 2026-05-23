package us.ajg0702.leaderboards.utils;

import org.bukkit.Bukkit;
import org.bukkit.OfflinePlayer;
import us.ajg0702.commands.CommandSender;
import us.ajg0702.leaderboards.LeaderboardPlugin;

import javax.annotation.Nullable;
import java.util.*;
import java.util.concurrent.ConcurrentLinkedDeque;
import java.util.concurrent.atomic.AtomicBoolean;

import static us.ajg0702.leaderboards.LeaderboardPlugin.message;

public class OfflineUpdater {
    private static final int BATCH_SIZE = 25;

    private final Deque<OfflinePlayer> offlinePlayerQueue = new ConcurrentLinkedDeque<>();
    private final LeaderboardPlugin plugin;
    private final CommandSender reportTo;
    private final int started;
    private final String board;
    private final long startedTime;
    private final AtomicBoolean finished = new AtomicBoolean(false);
    private volatile boolean cancelled = false;

    public OfflineUpdater(LeaderboardPlugin plugin, String board, OfflinePlayer[] players, @Nullable CommandSender reportTo) {
        this.plugin = plugin;
        this.board = board;
        this.reportTo = reportTo;
        offlinePlayerQueue.addAll(Arrays.asList(players));
        started = offlinePlayerQueue.size();
        startedTime = System.currentTimeMillis();

        scheduleNextBatch();
    }

    private void scheduleNextBatch() {
        if(cancelled || plugin.isShuttingDown()) {
            finish(true);
            return;
        }
        if(plugin.getTopManager().submit(this::runBatch) == null) {
            finish(true);
        }
    }

    private void runBatch() {
        if(cancelled || plugin.isShuttingDown()) {
            finish(true);
            return;
        }

        int processed = 0;
        while(processed < BATCH_SIZE && !offlinePlayerQueue.isEmpty() && !cancelled && !plugin.isShuttingDown()) {
            OfflinePlayer player = offlinePlayerQueue.poll();
            if(player == null) break;
            plugin.getCache().updateStat(board, player);
            processed++;
        }

        if(offlinePlayerQueue.isEmpty()) {
            finish(false);
            return;
        }

        if(cancelled || plugin.isShuttingDown()) {
            finish(true);
            return;
        }

        plugin.getScheduler().runTaskLaterAsynchronously(this::scheduleNextBatch, 1L);
    }

    public void cancel() {
        cancelled = true;
        offlinePlayerQueue.clear();
    }

    private void finish(boolean canceled) {
        if(!finished.compareAndSet(false, true)) return;
        plugin.getOfflineUpdaters().remove(board, this);
        if(canceled || plugin.isShuttingDown()) {
            plugin.getLogger().info("[OfflineUpdater] " + board + ": Canceling due to plugin shutdown");
            return;
        }

        long duration = System.currentTimeMillis() - startedTime;
        double durationSeconds = Math.round(duration / 10d) / 100d;
        plugin.getLogger().info("[OfflineUpdater] " + board + ": Finished in " + durationSeconds + "s " + duration);
        if(reportTo != null) {
            reportTo.sendMessage(message(
                    "&aFinished updating all offline players for &f" + board + " &ain&f " + durationSeconds + "&as"
            ));
        }
    }
    public double getProgressPercent() {
        if (started == 0) return 1; // No players started, avoid division by zero
        return (started - offlinePlayerQueue.size()) / ((double) started);
    }
    public int getRemainingPlayers() {
        return offlinePlayerQueue.size();
    }
    public int getDonePlayers() {
        return started - offlinePlayerQueue.size();
    }

    public int getStarted() {
        return started;
    }

    public boolean isDone() {
        return getRemainingPlayers() == 0;
    }

    public void progressLog() {
        plugin.getLogger().info(
                "[OfflineUpdater] " + board + ": " +
                        Math.round(getProgressPercent() * 1000)/10 + "% done " +
                        "(" + getRemainingPlayers() + " / " + getStarted() + ")"
        );
    }
}
