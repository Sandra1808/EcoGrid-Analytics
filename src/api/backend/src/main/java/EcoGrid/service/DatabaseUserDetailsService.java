package EcoGrid.service;

import EcoGrid.dao.UsuarioRepository;
import EcoGrid.entity.Usuario;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Locale;

@Service
public class DatabaseUserDetailsService implements UserDetailsService {

    private final UsuarioRepository usuarioRepository;
    private final String tenantCif;

    public DatabaseUserDetailsService(
            UsuarioRepository usuarioRepository,
            @Value("${app.tenant.cif:}") String tenantCif) {
        this.usuarioRepository = usuarioRepository;
        this.tenantCif = tenantCif;
    }

    @Override
    @Transactional(readOnly = true)
    public UserDetails loadUserByUsername(String email) {
        if (tenantCif.isBlank()) {
            throw new UsernameNotFoundException("Credenciales no válidas");
        }

        Usuario usuario = usuarioRepository
                .findByCifAndEmailIgnoreCase(tenantCif, email.trim())
                .filter(u -> Boolean.TRUE.equals(u.getActivo()))
                .orElseThrow(() ->
                        new UsernameNotFoundException("Credenciales no válidas"));

        String rol = usuario.getIdrol().getRol().trim().toUpperCase(Locale.ROOT);
        String autoridad = rol.startsWith("ROLE_") ? rol : "ROLE_" + rol;

        return User.withUsername(usuario.getEmail())
                .password(usuario.getPasswdHash())
                .authorities(autoridad)
                .build();
    }
}
