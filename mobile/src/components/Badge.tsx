import React from "react";
import { View, Text, StyleSheet, ViewStyle, TextStyle } from "react-native";
import { colors, spacing, fontSize } from "../constants/theme";

interface BadgeProps {
  label: string;
  color?: string;
  textColor?: string;
  style?: ViewStyle;
}

export function Badge({ label, color, textColor, style }: BadgeProps) {
  const badgeBackground = color ?? colors.surfaceLight;
  const badgeText = textColor ?? colors.text;

  return (
    <View style={[styles.badge, { backgroundColor: badgeBackground }, style]}>
      <Text style={[styles.label, { color: badgeText }]}>{label}</Text>
    </View>
  );
}

/** Returns a color based on match status. */
export function getStatusColor(status: string): string {
  switch (status) {
    case "live":
      return colors.success;
    case "finished":
      return colors.textSecondary;
    case "postponed":
      return colors.danger;
    case "scheduled":
    default:
      return colors.primary;
  }
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: 6,
    alignSelf: "flex-start",
  },
  label: {
    fontSize: fontSize.xs,
    fontWeight: "600",
  },
});
