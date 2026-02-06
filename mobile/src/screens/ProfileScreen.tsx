import React from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
} from "react-native";
import Constants from "expo-constants";
import { Ionicons } from "@expo/vector-icons";
import { useAuth } from "../lib/auth-context";
import { Card } from "../components/Card";
import { colors, spacing, fontSize } from "../constants/theme";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SettingsItemProps {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  onPress: () => void;
}

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

function SettingsItem({ icon, label, onPress }: SettingsItemProps) {
  return (
    <TouchableOpacity style={styles.settingsItem} onPress={onPress}>
      <View style={styles.settingsLeft}>
        <Ionicons name={icon} size={20} color={colors.textSecondary} />
        <Text style={styles.settingsLabel}>{label}</Text>
      </View>
      <Ionicons name="chevron-forward" size={18} color={colors.textSecondary} />
    </TouchableOpacity>
  );
}

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

export function ProfileScreen() {
  const { user, signOut } = useAuth();

  const appVersion =
    Constants.expoConfig?.version ?? Constants.manifest2?.extra?.expoClient?.version ?? "1.0.0";

  const createdAt = user?.created_at
    ? new Date(user.created_at).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : "N/A";

  const handleSignOut = () => {
    Alert.alert("Sign Out", "Are you sure you want to sign out?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Sign Out",
        style: "destructive",
        onPress: signOut,
      },
    ]);
  };

  const handleSettingsPress = (item: string) => {
    console.log("Settings pressed:", item);
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.scrollContent}
    >
      {/* User Info */}
      <Card style={styles.userCard}>
        <View style={styles.avatarCircle}>
          <Ionicons name="person" size={32} color={colors.primary} />
        </View>
        <Text style={styles.email}>{user?.email ?? "Unknown"}</Text>
        <Text style={styles.memberSince}>Member since {createdAt}</Text>
      </Card>

      {/* Settings */}
      <Text style={styles.sectionTitle}>Settings</Text>
      <Card style={styles.settingsCard}>
        <SettingsItem
          icon="notifications-outline"
          label="Notifications"
          onPress={() => handleSettingsPress("notifications")}
        />
        <View style={styles.separator} />
        <SettingsItem
          icon="language-outline"
          label="Language"
          onPress={() => handleSettingsPress("language")}
        />
        <View style={styles.separator} />
        <SettingsItem
          icon="moon-outline"
          label="Appearance"
          onPress={() => handleSettingsPress("appearance")}
        />
      </Card>

      {/* About */}
      <Text style={styles.sectionTitle}>About</Text>
      <Card style={styles.settingsCard}>
        <SettingsItem
          icon="document-text-outline"
          label="Terms of Service"
          onPress={() => handleSettingsPress("terms")}
        />
        <View style={styles.separator} />
        <SettingsItem
          icon="shield-checkmark-outline"
          label="Privacy Policy"
          onPress={() => handleSettingsPress("privacy")}
        />
      </Card>

      {/* App Version */}
      <Text style={styles.versionText}>WinRate AI v{appVersion}</Text>

      {/* Sign Out */}
      <TouchableOpacity style={styles.signOutButton} onPress={handleSignOut}>
        <Ionicons
          name="log-out-outline"
          size={20}
          color={colors.white}
          style={styles.signOutIcon}
        />
        <Text style={styles.signOutText}>Sign Out</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scrollContent: {
    padding: spacing.md,
    paddingBottom: spacing.xl * 2,
  },
  userCard: {
    alignItems: "center",
    paddingVertical: spacing.lg,
    marginBottom: spacing.lg,
  },
  avatarCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: colors.surfaceLight,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: spacing.md,
  },
  email: {
    fontSize: fontSize.lg,
    fontWeight: "bold",
    color: colors.text,
    marginBottom: spacing.xs,
  },
  memberSince: {
    fontSize: fontSize.sm,
    color: colors.textSecondary,
  },
  sectionTitle: {
    fontSize: fontSize.xs,
    fontWeight: "600",
    color: colors.textSecondary,
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginBottom: spacing.sm,
    marginLeft: spacing.xs,
  },
  settingsCard: {
    padding: 0,
    marginBottom: spacing.lg,
    overflow: "hidden",
  },
  settingsItem: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.md,
  },
  settingsLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
  },
  settingsLabel: {
    fontSize: fontSize.md,
    color: colors.text,
  },
  separator: {
    height: 1,
    backgroundColor: colors.border,
    marginLeft: spacing.md + 20 + spacing.md,
  },
  versionText: {
    fontSize: fontSize.xs,
    color: colors.textSecondary,
    textAlign: "center",
    marginBottom: spacing.lg,
  },
  signOutButton: {
    backgroundColor: colors.danger,
    borderRadius: 12,
    paddingVertical: spacing.sm + 4,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
  },
  signOutIcon: {
    marginRight: spacing.sm,
  },
  signOutText: {
    color: colors.white,
    fontSize: fontSize.md,
    fontWeight: "600",
  },
});
