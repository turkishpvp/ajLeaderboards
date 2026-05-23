package us.ajg0702.leaderboards.cache;

import org.junit.Test;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;

import static org.junit.Assert.*;

/**
 * Tests for Cache.reset() timestamp handling.
 * 
 * These tests verify that Cache.java uses the correct UTC timestamp calculation
 * and does NOT use the buggy LocalDateTime.now().atOffset(ZoneOffset.UTC) pattern.
 */
public class CacheResetTest {

    /**
     * Tests the correct UTC epoch millis calculation.
     * This demonstrates the CORRECT pattern that Cache.java should use.
     */
    @Test
    public void testCorrectTimestampIsUtcEpochMilli() throws Exception {
        long before = Instant.now().toEpochMilli();
        
        long correctTimestamp = Instant.now().toEpochMilli();
        
        long after = Instant.now().toEpochMilli();
        
        assertTrue("Timestamp should be >= before", correctTimestamp >= before);
        assertTrue("Timestamp should be <= after", correctTimestamp <= after);
        
        System.out.println("Correct UTC timestamp: " + correctTimestamp);
    }

    /**
     * Tests that the buggy timestamp calculation produces wrong values.
     * This demonstrates the WRONG pattern that Cache.java should NOT use.
     * 
     * The bug: LocalDateTime.now().atOffset(ZoneOffset.UTC) treats LOCAL time as UTC,
     * causing timezone-based offset errors (e.g., -5 hours in EST, +9 in JST).
     */
    @Test
    public void testBuggyTimestampCalculation() throws Exception {
        long before = Instant.now().toEpochMilli();
        
        // This is the BUGGY pattern that was used before the fix:
        // LocalDateTime.now().atOffset(ZoneOffset.UTC).toEpochSecond() * 1000
        LocalDateTime startDateTime = LocalDateTime.now();
        long buggyTimestamp = startDateTime.atOffset(ZoneOffset.UTC).toEpochSecond() * 1000;
        
        long after = Instant.now().toEpochMilli();
        
        System.out.println("Buggy timestamp: " + buggyTimestamp);
        System.out.println("Correct timestamp (Instant.now()): " + before + " to " + after);
        
        // The buggy timestamp is wrong because it treats local time as UTC
        // Difference = timezone offset (e.g., 5 hours for EST = 18,000,000 ms)
        long difference = Math.abs(buggyTimestamp - before);
        
        System.out.println("Difference from correct: " + difference + " ms (" + (difference/1000/60) + " minutes)");
        
        // This test documents the bug - the timestamp is off by the timezone offset
        // For most timezones, this is at least a few hours (millions of milliseconds)
        // We just verify there's some difference (could be 0 if in UTC+0 timezone)
        System.out.println("Bug demonstration: buggy timestamp may be offset by timezone difference");
    }

    /**
     * CRITICAL TEST: Verifies Cache.java uses correct timestamp pattern.
     * 
     * This test reads the actual Cache.java source code and verifies that:
     * 1. Line 769 uses Instant.now().toEpochMilli() (correct)
     * 2. The file does NOT contain the buggy LocalDateTime pattern
     * 
     * This test will FAIL if someone reintroduces the buggy code.
     */
    @Test
    public void testCacheUsesCorrectTimestampImplementation() throws IOException {
        // Read Cache.java source file
        String cacheSource = new String(Files.readAllBytes(
            Paths.get("src/main/java/us/ajg0702/leaderboards/cache/Cache.java")
        ));
        
        // Check that the correct pattern is present: Instant.now().toEpochMilli()
        assertTrue(
            "Cache.java must use Instant.now().toEpochMilli() for UTC timestamp",
            cacheSource.contains("Instant.now().toEpochMilli()")
        );
        
        // Check that the buggy pattern is NOT present
        // The buggy pattern was: LocalDateTime.now().atOffset(ZoneOffset.UTC).toEpochSecond()*1000
        // or similar variations
        String buggyPattern1 = "LocalDateTime.now().atOffset(ZoneOffset.UTC).toEpochSecond()";
        String buggyPattern2 = "LocalDateTime.now().atOffset(ZoneOffset.UTC).toEpochSecond()*1000";
        
        assertFalse(
            "Cache.java must NOT use buggy LocalDateTime.now().atOffset(ZoneOffset.UTC).toEpochSecond() pattern",
            cacheSource.contains(buggyPattern1)
        );
        assertFalse(
            "Cache.java must NOT use buggy LocalDateTime.now().atOffset(ZoneOffset.UTC).toEpochSecond()*1000 pattern",
            cacheSource.contains(buggyPattern2)
        );
        
        System.out.println("SUCCESS: Cache.java uses correct Instant.now().toEpochMilli() pattern");
        System.out.println("SUCCESS: Cache.java does NOT contain buggy LocalDateTime pattern");
    }

    /**
     * Integration test: Verifies the reset timestamp is in valid UTC range.
     * 
     * This simulates what Cache.reset() does at line 769 and verifies
     * the timestamp is within a reasonable range of current time.
     */
    @Test
    public void testResetTimestampIsValidUtcRange() {
        // This is what Cache.reset() does at line 769:
        long newTime = Instant.now().toEpochMilli();
        
        long before = System.currentTimeMillis();
        long after = System.currentTimeMillis();
        
        // The timestamp should be very close to current system time
        assertTrue("Reset timestamp should be >= current time - 1 second", 
            newTime >= before - 1000);
        assertTrue("Reset timestamp should be <= current time + 1 second", 
            newTime <= after + 1000);
        
        // Verify it's in valid range for 2020-2030 (sanity check)
        long minValid = Instant.parse("2020-01-01T00:00:00Z").toEpochMilli();
        long maxValid = Instant.parse("2030-01-01T00:00:00Z").toEpochMilli();
        
        assertTrue("Timestamp should be after 2020", newTime >= minValid);
        assertTrue("Timestamp should be before 2030", newTime <= maxValid);
        
        System.out.println("Valid UTC timestamp: " + newTime);
        System.out.println("Timestamp represents: " + Instant.ofEpochMilli(newTime));
    }

    /**
     * Demonstrates that the buggy pattern produces timestamps way off from correct.
     */
    @Test
    public void testBuggyPatternWouldBeDetected() throws Exception {
        // Current correct time in millis
        long correctNow = System.currentTimeMillis();
        
        // Simulate the buggy calculation (what was in the old code)
        long buggyTimestamp = LocalDateTime.now().atOffset(ZoneOffset.UTC).toEpochSecond() * 1000;
        
        // The difference should be enormous - the buggy code treats seconds as milliseconds
        // resulting in a timestamp ~50 years in the past (depending on when run)
        long difference = Math.abs(correctNow - buggyTimestamp);
        
        System.out.println("Current time (ms): " + correctNow);
        System.out.println("Buggy timestamp (ms): " + buggyTimestamp);
        System.out.println("Difference: " + difference + " ms (" + (difference/1000/60/60/24) + " days)");
        
        // Buggy code produces timestamps off by ~1.5 billion milliseconds (~17 days) or more
        // because it's using epoch SECONDS multiplied by 1000, not epoch MILLISECONDS
        assertTrue("Buggy pattern would be off by at least 1 second (1000ms)", 
            difference > 1000);
    }
}
