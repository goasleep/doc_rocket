import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"

import {
  type login as AccessToken,
  AuthService,
  type UserRead,
  type UserCreate,
  UsersService,
} from "@/client"
import { handleError } from "@/utils"
import useCustomToast from "./useCustomToast"

const isLoggedIn = () => {
  return localStorage.getItem("access_token") !== null
}

const useAuth = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { showErrorToast } = useCustomToast()

  const { data: user } = useQuery<UserRead | null, Error>({
    queryKey: ["currentUser"],
    queryFn: UsersService.usersCurrentUser,
    enabled: isLoggedIn(),
  })

  const signUpMutation = useMutation({
    mutationFn: (data: UserCreate) =>
      AuthService.registerRegister({ requestBody: data }),
    onSuccess: () => {
      navigate({ to: "/login" })
    },
    onError: (error: any) => {
      const detail = error?.body?.detail
      const message =
        detail === "REGISTER_USER_ALREADY_EXISTS"
          ? "The user with this email already exists in the system"
          : detail ?? "Something went wrong."
      showErrorToast(message)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })

  const login = async (data: AccessToken) => {
    const response = await AuthService.authJwtLogin({
      formData: data,
    })
    localStorage.setItem("access_token", response.access_token)
  }

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess: () => {
      navigate({ to: "/" })
    },
    onError: handleError.bind(showErrorToast),
  })

  const logout = () => {
    localStorage.removeItem("access_token")
    navigate({ to: "/login" })
  }

  return {
    signUpMutation,
    loginMutation,
    logout,
    user,
  }
}

export { isLoggedIn }
export default useAuth
