import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { ActivityIndicator, View } from "react-native";
import { useAuth } from "../lib/auth-context";
import { MainTabs } from "./MainTabs";
import { LoginScreen } from "../screens/auth/LoginScreen";
import { SignUpScreen } from "../screens/auth/SignUpScreen";
import { MatchDetailScreen } from "../screens/MatchDetailScreen";
import { colors } from "../constants/theme";

export type RootStackParamList = {
  Auth: undefined;
  Login: undefined;
  SignUp: undefined;
  Main: undefined;
  MatchDetail: { matchId: number };
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export function RootNavigator() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <View
        style={{
          flex: 1,
          justifyContent: "center",
          alignItems: "center",
          backgroundColor: colors.background,
        }}
      >
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.background },
        headerTintColor: colors.text,
        headerTitleStyle: { fontWeight: "bold" },
        contentStyle: { backgroundColor: colors.background },
      }}
    >
      {user ? (
        <>
          <Stack.Screen
            name="Main"
            component={MainTabs}
            options={{ headerShown: false }}
          />
          <Stack.Screen
            name="MatchDetail"
            component={MatchDetailScreen}
            options={{ title: "Match Details" }}
          />
        </>
      ) : (
        <>
          <Stack.Screen
            name="Login"
            component={LoginScreen}
            options={{ headerShown: false }}
          />
          <Stack.Screen
            name="SignUp"
            component={SignUpScreen}
            options={{ title: "Create Account" }}
          />
        </>
      )}
    </Stack.Navigator>
  );
}
