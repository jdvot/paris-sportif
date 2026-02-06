import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Ionicons } from "@expo/vector-icons";
import { PicksScreen } from "../screens/PicksScreen";
import { MatchesScreen } from "../screens/MatchesScreen";
import { TennisScreen } from "../screens/TennisScreen";
import { BasketballScreen } from "../screens/BasketballScreen";
import { DashboardScreen } from "../screens/DashboardScreen";
import { ProfileScreen } from "../screens/ProfileScreen";
import { colors } from "../constants/theme";

const Tab = createBottomTabNavigator();

export function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        tabBarStyle: {
          backgroundColor: colors.background,
          borderTopColor: colors.border,
        },
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textSecondary,
        headerStyle: { backgroundColor: colors.background },
        headerTintColor: colors.text,
      }}
    >
      <Tab.Screen
        name="Picks"
        component={PicksScreen}
        options={{
          title: "Daily Picks",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="star" size={size} color={color} />
          ),
        }}
      />
      <Tab.Screen
        name="Matches"
        component={MatchesScreen}
        options={{
          title: "Matches",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="football" size={size} color={color} />
          ),
        }}
      />
      <Tab.Screen
        name="Tennis"
        component={TennisScreen}
        options={{
          title: "Tennis",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="tennisball" size={size} color={color} />
          ),
        }}
      />
      <Tab.Screen
        name="Basketball"
        component={BasketballScreen}
        options={{
          title: "Basketball",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="basketball" size={size} color={color} />
          ),
        }}
      />
      <Tab.Screen
        name="Dashboard"
        component={DashboardScreen}
        options={{
          title: "Dashboard",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="bar-chart" size={size} color={color} />
          ),
        }}
      />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{
          title: "Profile",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="person" size={size} color={color} />
          ),
        }}
      />
    </Tab.Navigator>
  );
}
