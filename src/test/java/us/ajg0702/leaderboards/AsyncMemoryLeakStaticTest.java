package us.ajg0702.leaderboards;

import org.junit.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class AsyncMemoryLeakStaticTest {

    private String source(String path) throws IOException {
        return new String(Files.readAllBytes(Paths.get(path)));
    }

    @Test
    public void fetchQueueIsBoundedToSafeLimit() throws IOException {
        String topManager = source("src/main/java/us/ajg0702/leaderboards/boards/TopManager.java");

        assertFalse("Fetch queue must not allow a million queued tasks",
                topManager.contains("LinkedBlockingQueue<>(1000000)"));
        assertTrue("Fetch queue should use the named safe bound",
                topManager.contains("MAX_FETCH_QUEUE_SIZE"));
    }

    @Test
    public void quitUpdateIsScheduledAsynchronously() throws IOException {
        String listeners = source("src/main/java/us/ajg0702/leaderboards/Listeners.java");

        assertTrue("Quit stat update should be scheduled asynchronously",
                listeners.contains("runTaskAsynchronously(() -> plugin.getCache().updatePlayerStats(e.getPlayer()))"));
        assertFalse("Quit stat update should not run directly on the event thread",
                listeners.contains("if(!plugin.getAConfig().getBoolean(\"update-on-leave\")) return;\n\t\tplugin.getCache().updatePlayerStats"));
    }

    @Test
    public void shutdownClearsManagerCachesAndDoesNotKillWorkersDirectly() throws IOException {
        String plugin = source("src/main/java/us/ajg0702/leaderboards/LeaderboardPlugin.java");

        assertTrue(plugin.contains("offlineUpdaters.values().forEach(OfflineUpdater::cancel)"));
        assertTrue(plugin.contains("getPlaceholderFormatter().clearCache()"));
        assertTrue(plugin.contains("getSignManager().shutdown()"));
        assertTrue(plugin.contains("getHeadManager().clearCache()"));
        assertTrue(plugin.contains("getArmorStandManager().clearCache()"));
        assertFalse("Shutdown should not directly interrupt Bukkit worker threads",
                plugin.contains("killWorkers(100"));
        assertFalse("Shutdown should not directly interrupt Bukkit worker threads",
                plugin.contains("getThread().interrupt()"));
    }

    @Test
    public void headUtilsCacheClearUpdatesTimestampAndCapsCaches() throws IOException {
        String headUtils = source("nms/nms-legacy/src/main/java/us/ajg0702/leaderboards/nms/legacy/HeadUtils.java");

        assertFalse("lastClear must be mutable so cache clearing is not repeated forever",
                headUtils.contains("final long lastClear"));
        assertTrue("Clearing the skin cache must refresh lastClear",
                headUtils.contains("lastClear = System.currentTimeMillis()"));
        assertTrue("Head/url caches should have a hard maximum size",
                headUtils.contains("MAX_HEAD_CACHE_SIZE"));
        assertTrue("OkHttp resources should be shut down on plugin disable",
                headUtils.contains("httpClient.dispatcher().executorService().shutdown()"));
    }

    @Test
    public void quitCleanupDoesNotRequireBoardPlayerClass() throws IOException {
        String cache = source("src/main/java/us/ajg0702/leaderboards/cache/Cache.java");
        int cleanPlayerStart = cache.indexOf("public void cleanPlayer");
        int cleanPlayerEnd = cache.indexOf("public List<String> getNonExistantBoards()");
        String cleanPlayerSection = cache.substring(cleanPlayerStart, cleanPlayerEnd);

        assertFalse("Logout cleanup should not load BoardPlayer",
                cleanPlayerSection.contains("BoardPlayer"));
        assertTrue("Zero-validation cleanup should use simple string keys",
                cache.contains("List<String> zeroPlayers"));
    }
}
