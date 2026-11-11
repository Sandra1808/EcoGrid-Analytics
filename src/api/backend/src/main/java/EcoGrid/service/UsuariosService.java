package EcoGrid.service;

import EcoGrid.dao.UsuarioRepository;
import EcoGrid.dto.UsuarioResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@Service
public class UsuariosService {

    private final UsuarioRepository repository;
    private final String cif;

    public UsuariosService(
            UsuarioRepository repository,
            @Value("${app.tenant.cif:}") String cif) {
        this.repository = repository;
        this.cif = cif;
    }

    @Transactional(readOnly = true)
    public List<UsuarioResponse> listar() {
        if (cif.isBlank()) {
            throw new ResponseStatusException(
                    HttpStatus.SERVICE_UNAVAILABLE,
                    "Configura app.tenant.cif para consultar los usuarios");
        }

        return repository.findByCifOrderByNombreAsc(cif)
                .stream()
                .map(usuario -> new UsuarioResponse(
                        usuario.getId(),
                        usuario.getNombre(),
                        usuario.getEmail(),
                        usuario.getCif(),
                        usuario.getIdrol().getRol(),
                        Boolean.TRUE.equals(usuario.getActivo())
                                ? "Activo"
                                : "Inactivo",
                        usuario.getFeccreacion()))
                .toList();
    }
}